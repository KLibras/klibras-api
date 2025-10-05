from pydantic import BaseModel, ConfigDict

class SignRead(BaseModel):
    id: int
    name: str
    desc: str
    videoUrl: str
    pontos: int

    model_config = ConfigDict(from_attributes=True)