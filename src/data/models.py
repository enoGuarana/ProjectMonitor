from datetime import date, datetime
from enum import Enum, auto
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class ProjectStatus(Enum):
    PLANEJAMENTO = "planejamento"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    PARALISADO = "paralisado"
    CANCELADO = "cancelado"

class RiskLevel(Enum):
    BAIXO = "baixo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"

class Milestone(BaseModel):
    id: str
    title: str
    expected_date: date
    actual_date: Optional[date] = None
    status: str = Field(default="pendente")  # pendente, concluido, atrasado
    
    @property
    def is_overdue(self) -> bool:
        if self.actual_date or self.status == "concluido":
            return False
        return date.today() > self.expected_date
    
    @property
    def days_until(self) -> Optional[int]:
        if self.actual_date or self.status == "concluido":
            return None
        return (self.expected_date - date.today()).days

class ProjectUpdate(BaseModel):
    """Representa uma atualização/ notícia sobre o projeto"""
    id: str
    project_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str  # "sharepoint", "email", "teams", "manual"
    title: str
    description: str
    category: str = Field(default="geral")  # "marco", "risco", "decisao", "documento"
    url: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    area_responsavel: str  # ex: "CGIN", "DNT"
    responsible_team: List[str]  # emails ou grupos
    status: ProjectStatus = ProjectStatus.EM_ANDAMENTO
    risk_level: RiskLevel = RiskLevel.BAIXO
    
    # Prazos
    start_date: date
    expected_end_date: date
    milestones: List[Milestone] = Field(default_factory=list)
    
    # Metadados
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)
    
    # Cache de atualizações recentes
    recent_updates: List[ProjectUpdate] = Field(default_factory=list)
    
    @property
    def days_until_deadline(self) -> Optional[int]:
        if self.status == ProjectStatus.CONCLUIDO:
            return None
        return (self.expected_end_date - date.today()).days
    
    @property
    def is_at_risk(self) -> bool:
        """Projeto em risco: vencendo em <=15 dias OU com marco atrasado"""
        if self.days_until_deadline is not None and self.days_until_deadline <= 15:
            return True
        return any(m.is_overdue for m in self.milestones)
    
    @field_validator('expected_end_date')
    def end_must_be_after_start(cls, v, values):
        if 'start_date' in values.data and v < values.data['start_date']:
            raise ValueError('Data de término deve ser após data de início')
        return v
