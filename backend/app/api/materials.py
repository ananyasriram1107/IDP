from fastapi import APIRouter, HTTPException, UploadFile

from app.models.material import MaterialChunk, StudyMaterial
from app.services.material_service import (
    get_material_by_id,
    get_material_chunks,
    list_materials,
    save_and_process_material,
)

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("/upload", response_model=StudyMaterial)
async def upload_material(file: UploadFile) -> StudyMaterial:
    return await save_and_process_material(file)


@router.get("", response_model=list[StudyMaterial])
async def get_materials() -> list[StudyMaterial]:
    return await list_materials()


@router.get("/{material_id}", response_model=StudyMaterial)
async def get_material(material_id: str) -> StudyMaterial:
    material = await get_material_by_id(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Study material not found")
    return material


@router.get("/{material_id}/content", response_model=list[MaterialChunk])
async def get_material_content(material_id: str) -> list[MaterialChunk]:
    material = await get_material_by_id(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Study material not found")
    return await get_material_chunks(material_id)
