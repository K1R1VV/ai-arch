import os
from celery import Celery


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


celery_app = Celery(
    "movie_recommender",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.presentation.tasks"]
)


celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_time_limit=300,
    task_soft_time_limit=240,
)