from models import UserInput

schema = UserInput.model_json_schema()

print(schema)

user1 = UserInput(
    name="Apu",
    age=30,
    city="Bengaluru"
)

print(user1)

# Invalid input
user2 = UserInput(
    name="A",
    age=15
)

print(user2)