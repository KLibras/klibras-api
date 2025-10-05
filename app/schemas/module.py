from pydantic import BaseModel, ConfigDict
from typing import List
from .sign import SignRead

class ModuleRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ModuleWithSigns(ModuleRead):
   
    signs: List[SignRead] = []

    model_config = ConfigDict(from_attributes=True)