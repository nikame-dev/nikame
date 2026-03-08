from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Any
from pydantic import BaseModel
import json
import redis
import os

from app import models, database
from app.database import engine, get_db

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NIKAME Template Registry", version="1.0.0")

# Redis Cache setup
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    cache = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    cache = None

# Pydantic Schemas
class TemplateBase(BaseModel):
    name: str
    description: str
    tags: List[str] = []
    version: str = "1.0"
    
class TemplateCreate(TemplateBase):
    id: str
    raw_config: dict
    author: str

class TemplateResponse(TemplateBase):
    id: str
    stars: int
    downloads: int
    author: str
    verified: bool
    
    class Config:
        from_attributes = True

class TemplateDetailResponse(TemplateResponse):
    raw_config: dict

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/templates", response_model=List[TemplateResponse])
def search_templates(
    q: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = Query("stars", regex="^(stars|recent|name)$"),
    verified_only: bool = False,
    db: Session = Depends(get_db)
):
    """Search for templates with caching."""
    # Try Cache
    cache_key = f"search:{q}:{tag}:{sort_by}:{verified_only}"
    if cache:
        cached = cache.get(cache_key)
        if cached:
            return json.loads(cached)
            
    query = db.query(models.Template)
    
    if verified_only:
        query = query.filter(models.Template.verified == True)
        
    if tag:
        # PostgreSQL JSONB contains operator would be better, but testing with simple string match
        query = query.filter(models.Template.tags.cast(String).ilike(f"%{tag}%"))
        
    if q:
        search_filter = or_(
            models.Template.name.ilike(f"%{q}%"),
            models.Template.description.ilike(f"%{q}%"),
            models.Template.id.ilike(f"%{q}%")
        )
        query = query.filter(search_filter)
        
    if sort_by == "stars":
        query = query.order_by(models.Template.stars.desc())
    elif sort_by == "name":
        query = query.order_by(models.Template.name.asc())
    else:
        query = query.order_by(models.Template.created_at.desc())
        
    results = query.all()
    
    # Store in Cache for 60 seconds
    if cache:
        cache.setex(cache_key, 60, json.dumps([r.__dict__ for r in results], default=str))
        
    return results

@app.get("/templates/mine", response_model=List[TemplateResponse])
def get_my_templates(
    author: str, # In a real app this would come from Auth token
    db: Session = Depends(get_db)
):
    return db.query(models.Template).filter(models.Template.author == author).all()

@app.get("/templates/{template_id}", response_model=TemplateDetailResponse)
def get_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    # Increment downloads randomly or based on real usage
    template.downloads += 1
    db.commit()
    return template

@app.post("/templates", status_code=status.HTTP_201_CREATED)
def publish_template(
    template_in: TemplateCreate,
    author_token: str = None, # Simple mock auth
    db: Session = Depends(get_db)
):
    """Publish a new template."""
    existing = db.query(models.Template).filter(models.Template.id == template_in.id).first()
    if existing:
        if existing.author != template_in.author:
            raise HTTPException(status_code=403, detail="Not authorized to update this template")
        # Update
        existing.name = template_in.name
        existing.description = template_in.description
        existing.tags = template_in.tags
        existing.raw_config = template_in.raw_config
        existing.version = template_in.version
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "id": existing.id}
    else:
        # Create
        new_template = models.Template(
            id=template_in.id,
            name=template_in.name,
            description=template_in.description,
            tags=template_in.tags,
            author=template_in.author,
            raw_config=template_in.raw_config,
            version=template_in.version
        )
        db.add(new_template)
        db.commit()
        db.refresh(new_template)
        
        # Invalidate cache
        if cache:
            keys = cache.keys("search:*")
            if keys:
                cache.delete(*keys)
                
        return {"status": "created", "id": new_template.id}

@app.post("/templates/{template_id}/star")
def star_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    template.stars += 1
    db.commit()
    
    if cache:
        keys = cache.keys("search:*")
        if keys:
            cache.delete(*keys)
            
    return {"status": "starred", "stars": template.stars}

@app.post("/templates/{template_id}/unstar")
def unstar_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    template.stars = max(0, template.stars - 1)
    db.commit()
    
    if cache:
        keys = cache.keys("search:*")
        if keys:
            cache.delete(*keys)
            
    return {"status": "unstarred", "stars": template.stars}
