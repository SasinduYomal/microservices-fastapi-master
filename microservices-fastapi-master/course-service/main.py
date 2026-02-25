from fastapi import FastAPI

app = FastAPI(title="Course Microservice")

courses = [
    {"id": 1, "name": "Data Science", "duration": "6 Months"},
    {"id": 2, "name": "Cyber Security", "duration": "4 Months"}
]

@app.get("/")
def root():
    return {"message": "Course Service running"}

@app.get("/api/courses")
def get_courses():
    return courses
