from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    filename: str
    page: Optional[int] = None
    sheet: Optional[str] = None
    excerpt: str = ""
    source_type: str

class BOQItem(BaseModel):
    item_code: str = ""
    description: str
    unit: str = ""
    quantity: float = 0.0
    unit_rate: Optional[float] = None
    amount: Optional[float] = None
    csi_code: str = "00 00 00"
    section: str = ""
    evidence: list[Evidence] = Field(default_factory=list)

class SpecSection(BaseModel):
    csi_code: str
    title: str
    division: str = ""
    body_preview: str = ""
    evidence: list[Evidence] = Field(default_factory=list)

class ContractFinding(BaseModel):
    term: str
    value: str = ""
    excerpt: str
    evidence: list[Evidence] = Field(default_factory=list)

class DrawingElement(BaseModel):
    element_id: str
    text: str
    element_type: str = "TEXT"
    csi_code: str = "00 00 00"
    geometry: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    evidence: list[Evidence] = Field(default_factory=list)

class SamcoCandidate(BaseModel):
    master_code: str
    title: str
    score: float
    reason: str
    legacy_code: Optional[str] = None

class ScopeEntry(BaseModel):
    scope_key: str
    csi_code: str
    csi_title: str = ""
    division: str = ""
    boq_items: list[BOQItem] = Field(default_factory=list)
    spec_sections: list[SpecSection] = Field(default_factory=list)
    contract_references: list[ContractFinding] = Field(default_factory=list)
    drawing_elements: list[DrawingElement] = Field(default_factory=list)
    quantity_by_unit: dict[str, float] = Field(default_factory=dict)
    completeness: dict[str, bool] = Field(default_factory=dict)
    conflicts: list[str] = Field(default_factory=list)
    samco_candidates: list[SamcoCandidate] = Field(default_factory=list)
    selected_samco_code: Optional[str] = None
    mapping_status: str = "unmapped"
    mapping_confidence: float = 0.0

class DocumentResult(BaseModel):
    filename: str
    document_type: str
    pages: int = 0
    chars: int = 0
    extraction_mode: str = "native"
    needs_ocr: bool = False
    warnings: list[str] = Field(default_factory=list)

class IntegratedProject(BaseModel):
    project_code: str
    project_name: str
    ingestion_id: str
    source_files: list[str] = Field(default_factory=list)
    documents: list[DocumentResult] = Field(default_factory=list)
    scope_entries: list[ScopeEntry] = Field(default_factory=list)
    coverage: dict[str, int] = Field(default_factory=dict)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unmapped_scope: list[str] = Field(default_factory=list)
    status: str = "ready"
