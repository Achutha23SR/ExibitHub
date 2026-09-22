from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, uuid, logging, bcrypt, jwt

ROOT_DIR = Path(__file__).parent
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
app = FastAPI(title="EventAtlas API")
api = APIRouter(prefix="/api")
JWT_ALGORITHM = "HS256"

class EventInput(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10)
    category: str
    industry: str
    start_date: str
    end_date: str
    venue: str
    city: str
    country: str
    organizer: str
    organizer_email: EmailStr
    website: str
    image_url: str
    status: str = "published"
    featured: bool = False

class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

def now(): return datetime.now(timezone.utc).isoformat()
def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def verify_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())
def token_for(user):
    return jwt.encode({"sub": user["id"], "email": user["email"], "role": user["role"], "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)

async def current_user(request: Request):
    raw = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not raw: raise HTTPException(401, "Authentication required")
    try: payload = jwt.decode(raw, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired session")
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not user: raise HTTPException(401, "User not found")
    return user

async def admin_user(user=Depends(current_user)):
    if user.get("role") != "admin": raise HTTPException(403, "Admin access required")
    return user

SEED_EVENTS = [
 {"name":"Global Retail Forum 2026","category":"Trade show","industry":"Retail & Commerce","start_date":"2026-04-14","end_date":"2026-04-16","venue":"ExCeL London","city":"London","country":"United Kingdom","organizer":"Northstar Events","organizer_email":"hello@northstar.events","website":"https://northstar.events","image_url":"https://images.unsplash.com/photo-1761195689615-9469b65dac01?auto=format&fit=crop&w=1200&q=85","description":"The meeting place for retail leaders shaping the next era of physical and digital commerce.","status":"published","featured":True},
 {"name":"Future of Work Summit","category":"Conference","industry":"Technology","start_date":"2026-05-06","end_date":"2026-05-07","venue":"Fira Barcelona","city":"Barcelona","country":"Spain","organizer":"Workplace Collective","organizer_email":"team@workplacecollective.com","website":"https://workplacecollective.com","image_url":"https://images.unsplash.com/photo-1759477274012-263d469f0e16?auto=format&fit=crop&w=1200&q=85","description":"Two focused days on the tools, culture, and leadership practices powering modern teams.","status":"published","featured":True},
 {"name":"Sustainable Industry Expo","category":"Exhibition","industry":"Manufacturing","start_date":"2026-06-18","end_date":"2026-06-20","venue":"RAI Amsterdam","city":"Amsterdam","country":"Netherlands","organizer":"Greenline Exhibitions","organizer_email":"info@greenlineexpo.com","website":"https://greenlineexpo.com","image_url":"https://images.unsplash.com/photo-1767507006455-538274e7be76?auto=format&fit=crop&w=1200&q=85","description":"Discover practical systems and partnerships accelerating the industrial transition to net zero.","status":"published","featured":False},
 {"name":"ScaleUp Capital Connect","category":"Business event","industry":"Finance & Investment","start_date":"2026-07-02","end_date":"2026-07-03","venue":"Marina Bay Sands","city":"Singapore","country":"Singapore","organizer":"Venture Assembly","organizer_email":"events@ventureassembly.co","website":"https://ventureassembly.co","image_url":"https://images.unsplash.com/photo-1675716921224-e087a0cca69a?auto=format&fit=crop&w=1200&q=85","description":"Curated conversations between ambitious founders, operators, and the capital partners behind growth.","status":"published","featured":False},
 {"name":"Design Systems Exchange","category":"Workshop","industry":"Design & Product","start_date":"2026-08-11","end_date":"2026-08-12","venue":"The Glasshouse","city":"New York","country":"United States","organizer":"Craft Bureau","organizer_email":"hello@craftbureau.design","website":"https://craftbureau.design","image_url":"https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=1200&q=85","description":"A hands-on exchange for product teams building coherent, accessible digital experiences at scale.","status":"published","featured":False}
]

@api.get("/")
async def root(): return {"message":"EventAtlas API online"}

@api.post("/auth/login")
async def login(data: LoginInput, response: Response):
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not verify_password(data.password, user["password_hash"]): raise HTTPException(401, "Incorrect email or password")
    safe = {"id":user["id"],"email":user["email"],"name":user["name"],"role":user["role"]}
    response.set_cookie("access_token", token_for(safe), httponly=True, secure=True, samesite="none", max_age=28800)
    return safe

@api.post("/auth/logout")
async def logout(response: Response): response.delete_cookie("access_token"); return {"ok":True}

@api.get("/auth/me")
async def me(user=Depends(current_user)): return user

@api.get("/events")
async def events(search: str = "", category: str = "all", industry: str = "all", status: str = "published", sort: str = "soonest", page: int = Query(1, ge=1), limit: int = Query(6, ge=1, le=50)):
    query = {}
    if status != "all": query["status"] = status
    if category != "all": query["category"] = category
    if industry != "all": query["industry"] = industry
    if search: query["$or"] = [{"name":{"$regex":search,"$options":"i"}},{"city":{"$regex":search,"$options":"i"}},{"country":{"$regex":search,"$options":"i"}},{"industry":{"$regex":search,"$options":"i"}}]
    ordering = [("start_date", 1)] if sort == "soonest" else [("start_date", -1)]
    total = await db.events.count_documents(query)
    data = await db.events.find(query, {"_id":0}).sort(ordering).skip((page-1)*limit).limit(limit).to_list(limit)
    return {"items":data,"total":total,"page":page,"pages":max(1,(total+limit-1)//limit)}

@api.get("/events/featured")
async def featured(): return await db.events.find({"featured":True,"status":"published"},{"_id":0}).sort("start_date",1).limit(3).to_list(3)

@api.get("/events/{event_id}")
async def event_detail(event_id: str):
    event = await db.events.find_one({"id":event_id},{"_id":0})
    if not event: raise HTTPException(404,"Event not found")
    return event

@api.get("/meta")
async def meta():
    return {"categories": await db.events.distinct("category"), "industries": await db.events.distinct("industry")}

@api.post("/events", dependencies=[Depends(admin_user)])
async def create_event(data: EventInput):
    event = data.model_dump(); event.update({"id":str(uuid.uuid4()),"created_at":now(),"updated_at":now()}); await db.events.insert_one(event); return await db.events.find_one({"id":event["id"]},{"_id":0})

@api.put("/events/{event_id}", dependencies=[Depends(admin_user)])
async def update_event(event_id: str, data: EventInput):
    event=data.model_dump(); event["updated_at"]=now(); result=await db.events.update_one({"id":event_id},{"$set":event})
    if not result.matched_count: raise HTTPException(404,"Event not found")
    return await db.events.find_one({"id":event_id},{"_id":0})

@api.delete("/events/{event_id}", dependencies=[Depends(admin_user)])
async def delete_event(event_id: str):
    result=await db.events.delete_one({"id":event_id})
    if not result.deleted_count: raise HTTPException(404,"Event not found")
    return {"ok":True}

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True); await db.events.create_index([("status",1),("start_date",1)]); await db.events.create_index([("featured",1),("start_date",1)])
    email=os.environ["ADMIN_EMAIL"].lower(); password=os.environ["ADMIN_PASSWORD"]
    existing=await db.users.find_one({"email":email})
    if not existing: await db.users.insert_one({"id":str(uuid.uuid4()),"email":email,"password_hash":hash_password(password),"name":"EventAtlas Admin","role":"admin","created_at":now()})
    if await db.events.count_documents({}) == 0:
        for event in SEED_EVENTS: event.update({"id":str(uuid.uuid4()),"created_at":now(),"updated_at":now()})
        await db.events.insert_many(SEED_EVENTS)

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=[os.environ["FRONTEND_URL"]], allow_methods=["*"], allow_headers=["*"])
logging.basicConfig(level=logging.INFO)