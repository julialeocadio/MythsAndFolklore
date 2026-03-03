class Config: 
    SECRET_KEY = "this_is_giving_me_a_headache"
    JWT_SECRET_KEY = "i_need_more_coffee"
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    API_KEY = "i_also_need_water"
    SQLALCHEMY_DATABASE_URI = "sqlite:///data.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False