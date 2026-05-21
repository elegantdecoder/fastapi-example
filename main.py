#in this API creation, we have first created methods without any database but the mock data, now after that we connected the database and then moved on created the methods again 

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Generic, Optional, TypeVar
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Session, create_engine, select


class Campaign(SQLModel, table=True):
    campaign_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    due_date: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

class CampaignCreate(SQLModel):
    name: str
    due_date: datetime | None = None 


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        if not session.exec(select(Campaign)).first():
            session.add_all([
                Campaign(name="Summer Launch", due_date=datetime.now(timezone.utc)),
                Campaign(name="Black Friday", due_date=datetime.now(timezone.utc))
            ])
            session.commit()
    yield 

app = FastAPI(root_path="/api/v1", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Hello World!"}

T = TypeVar("T")
class Response(BaseModel, Generic[T]):
    data: T

class PaginatedResponse(BaseModel, Generic[T]):
    data: T
    next: Optional[str]
    prev: Optional[str]
    
    
    

#creating methods with database
@app.get("/campaigns", response_model=PaginatedResponse[list[Campaign]])
async def read_campaign(request: Request, session: SessionDep, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1)): # type: ignore
    
    data = session.exec(select(Campaign).order_by(Campaign.campaign_id).offset(offset).limit(limit)).all() #type: ignore

    base_url = str(request.url).split('?')[0] # type: ignore

    next_url = f"{base_url}?offset={offset+limit}&limit={limit}"

    if offset > 0 :
        prev_url = f"{base_url}?offset={max(0, offset-limit)}&limit={limit}"
    else:
        prev_url = None
         
    #print(base_url)
    return {
        "next": next_url,
        "prev": prev_url,
        "data": data
    } # type: ignore

@app.get("/campaign/{id}", response_model=Response[Campaign])
async def read_campaign(id: int, session: SessionDep):
    data = session.get(Campaign, id)
    if not data:
        raise HTTPException(status_code=404)
    return {"data": data} 

@app.post("/campaign", status_code=201, response_model=Response[Campaign])
async def create_campaign(campaign: CampaignCreate, session:SessionDep):
    db_campaign = Campaign.model_validate(campaign)
    session.add(db_campaign) 
    session.commit()
    session.refresh(db_campaign)
    return {"data": db_campaign} 

@app.put("/campaigns/{id}", response_model=Response[Campaign])
async def update_campaign(id: int, campaign: CampaignCreate, session: SessionDep):
    data = session.get(Campaign, id)
    if not data:
        raise HTTPException(status_code=404)
    data.name = campaign.name
    data.due_date = campaign.due_date
    session.add(data)
    session.commit()
    session.refresh(data)
    return {"data": data}

@app.delete("/campaigns/{id}", status_code=204)
async def delete_campaign(id: int, session: SessionDep):
    data = session.get(Campaign, id)
    if not data:
        raise HTTPException(status_code=404)
    session.delete(data)
    session.commit()



# @app.put("/campaigns/{id}")
# async def update_campaign(id: int, body: dict[str, Any]):

#     for index, campaign in enumerate(data):
#         if campaign.get("campaign_id") == id:

#             updated: Any = {
#                 "campaign_id": id,
#                 "name": body.get("name"),
#                 "due_date": body.get("due_date"),
#                 "created_at": campaign.get("created_at")
#             }

#             data[index] = updated
#             return {"campaign": updated}
#     raise HTTPException(status_code=404)


# @app.delete("/campaigns/{id}")
# async def delete_campaign(id: int):

#     for index, campaign in enumerate(data):
#         if campaign.get("campaign_id") == id:
#             data.pop(index)
#             return Response(status_code=204)
#     raise HTTPException(status_code=404)
