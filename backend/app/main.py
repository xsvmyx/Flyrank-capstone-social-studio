from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_router, posts_router, upload_router
from routers import llm

app = FastAPI(
    title="Social Media Studio",
)

origins = [
    "http://localhost:3000",     
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(posts_router.router)
app.include_router(llm.router)
app.include_router(upload_router.router)


@app.get("/")
def read_root():
    return {"message": "API is running"}



