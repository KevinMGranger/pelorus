from attrs import define

# There's some tricky type system stuff that happens for attrs to work.
# This lets us avoid all their work, since config is just a thin wrapper over define.
config = define
