import os
import tempfile
from mydb import MyDB

def describe_mydb():

    def describe_init():

        def it_creates_file_and_assigns_name():
            with tempfile.TemporaryDirectory() as tmp:
                fname = os.path.join(tmp, "db.txt")
                db = MyDB(fname)
                assert db.fname == fname
                assert os.path.exists(fname)

    def describe_loadStrings():

        def it_returns_empty_list_for_new_db():
            with tempfile.TemporaryDirectory() as tmp:
                fname = os.path.join(tmp, "db.txt")
                db = MyDB(fname)
                assert db.loadStrings() == []

    def describe_saveStrings():

        def it_writes_array_and_loads_it_back():
            with tempfile.TemporaryDirectory() as tmp:
                fname = os.path.join(tmp, "db.txt")
                db = MyDB(fname)
                data = ["a", "b", "c"]
                db.saveStrings(data)
                assert db.loadStrings() == data

    def describe_saveString():

        def it_appends_to_existing_list():
            with tempfile.TemporaryDirectory() as tmp:
                fname = os.path.join(tmp, "db.txt")
                db = MyDB(fname)
                db.saveStrings(["x"])
                db.saveString("y")
                assert db.loadStrings() == ["x", "y"]

        def it_creates_file_and_appends_if_missing():
            with tempfile.TemporaryDirectory() as tmp:
                fname = os.path.join(tmp, "db.txt")
                db = MyDB(fname)
                db.saveString("first")
                assert db.loadStrings() == ["first"]
