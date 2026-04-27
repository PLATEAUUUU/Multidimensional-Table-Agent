# app/main.py

from fastapi import FastAPI

from app.api.exception_handlers import register_exception_handlers

app = FastAPI(title="Agent Interview System")

register_exception_handlers(app)