from typing import Annotated
import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, col


class Person(SQLModel, table=True):
    person_id: int | None = Field(default=None, primary_key=True)
    last_name: str = Field(index=True)
    first_name: str = Field(index=True)
    middle_name: str = Field(index=True)
    gender: str | None = Field(default=None, index=True)
    nationality: str | None = Field(default=None, index=True)
    age: int | None = Field(default=None, index=True)

    def __init__(self, last_name: str, first_name: str, middle_name: str):
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name


sqlite_file_name = "people_database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.post("/people/")
def create_person(first_name: str, last_name: str, middle_name: str, session: SessionDep):
    person = Person(last_name.strip().lower(), first_name.strip().lower(), middle_name.strip().lower())

    try:
        response = requests.get("https://api.nationalize.io/?name=" + person.first_name)
        if response.status_code == 200:
            person.nationality = response.json()["country"][0]["country_id"]
    except Exception as e:
        print("Exception: " + str(e))

    try:
        response = requests.get("https://api.agify.io?name=" + person.first_name + "&country_id=" + person.nationality)
        if response.status_code == 200:
            person.age = response.json()["age"]
    except Exception as e:
        print("Exception: " + str(e))

    try:
        response = requests.get(
            "https://api.genderize.io?name=" + person.first_name + "&country_id=" + person.nationality)
        if response.status_code == 200:
            person.gender = response.json()["gender"]
    except Exception as e:
        print("Exception: " + str(e))

    session.add(person)
    session.commit()
    session.refresh(person)
    return person


@app.get("/people/{person_id}")
def read_person(last_name: str, session: SessionDep):
    statement = select(Person).where(Person.last_name == last_name)
    results = session.exec(statement).all()
    if not results:
        raise HTTPException(status_code=404, detail="Person not found")
    return results


@app.post("/people/{person_id}")
def edit_person(session: SessionDep, person_id: int, first_name: str | None = None, last_name: str | None = None,
                middle_name: str | None = None, gender: str | None = None, nationality: str | None = None,
                age: int | None = None):
    statement = select(Person).where(Person.person_id == person_id)
    person = session.exec(statement).one()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if first_name is not None:
        person.first_name = first_name

    if last_name is not None:
        person.last_name = last_name

    if middle_name is not None:
        person.middle_name = middle_name

    if gender is not None:
        person.gender = gender

    if nationality is not None:
        person.nationality = nationality

    if age is not None:
        person.age = age

    session.add(person)
    session.commit()
    session.refresh(person)

    return person


@app.get("/people/")
def read_people(session: SessionDep):
    statement = select(Person)
    results = session.exec(statement).all()
    if not results:
        raise HTTPException(status_code=404, detail="Person not found")

    return results
