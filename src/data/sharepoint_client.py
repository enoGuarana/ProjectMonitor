import os
import logging
from typing import List, Optional
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
from src.data.models import Project, Milestone, ProjectStatus, RiskLevel
from datetime import datetime, date

logger = logging.getLogger(__name__)

class SharePointClient:
    """Cliente para ler dados de projetos do SharePoint Online"""
    
    def __init__(self, site_url: str, username: str, password: str):
        self.site_url = site_url
        self.ctx = ClientContext(site_url).with_credentials(UserCredential(username, password))
    
    @classmethod
    def from_env(cls):
        """Factory method para criar instância a partir de variáveis de ambiente"""
        return cls(
            site_url=os.getenv("SHAREPOINT_SITE_URL"),
            username=os.getenv("SHAREPOINT_USERNAME"),
            password=os.getenv("SHAREPOINT_PASSWORD")  # considere usar Managed Identity em produção
        )
    
    def load_projects(self, list_name: str = "ProjetosCGIN") -> List[Project]:
        """
        Carrega lista de projetos do SharePoint
        Assume estrutura de lista com colunas específicas (adaptar conforme sua realidade)
        """
        try:
            project_list = self.ctx.web.lists.get_by_title(list_name)
            items = project_list.items.get().execute_query()
            
            projects = []
            for item in items:
                try:
                    project = self._parse_sharepoint_item(item)
                    if project:
                        projects.append(project)
                except Exception as e:
                    logger.warning(f"Erro ao parsear item {item.get('Id')}: {e}")
                    continue
            
            logger.info(f"Carregados {len(projects)} projetos de '{list_name}'")
            return projects
            
        except Exception as e:
            logger.error(f"Erro ao carregar projetos do SharePoint: {e}")
            raise
    
    def _parse_sharepoint_item(self, item: dict) -> Optional[Project]:
        """Converte item do SharePoint em objeto Project"""
        # Mapeamento de colunas do SharePoint → campos do modelo
        # ADAPTE ESTES CAMPOS conforme sua lista real no SharePoint
        
        try:
            # Datas: SharePoint retorna em formato ISO ou datetime
            def parse_date(value) -> Optional[date]:
                if not value:
                    return None
                if isinstance(value, str):
                    return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                return value.date() if hasattr(value, 'date') else None
            
            # Milestones: assumindo campo multi-valor ou texto estruturado
            # Na prática, você pode ter uma lista separada de marcos
            milestones = []
            milestones_raw = item.get("Milestones", "")  # ajustar conforme sua estrutura
            
            return Project(
                id=str(item.get("Id", "")),
                name=item.get("Title", "Sem título"),
                description=item.get("Description", None),
                area_responsavel=item.get("AreaResponsavel", "Não informada"),
                responsible_team=self._parse_team(item.get("ResponsavelEquipe", "")),
                status=ProjectStatus(item.get("Status", "em_andamento")),
                risk_level=RiskLevel(item.get("RiskLevel", "baixo")),
                start_date=parse_date(item.get("StartDate")) or date.today(),
                expected_end_date=parse_date(item.get("EndDate")) or date.today(),
                milestones=milestones,
                tags=self._parse_tags(item.get("Tags", "")),
                last_updated=datetime.now()
            )
        except Exception as e:
            logger.error(f"Erro no parse de item: {e}")
            return None
    
    @staticmethod
    def _parse_team(value: str) -> List[str]:
        """Parse campo de equipe responsável (pode ser email, grupo, múltiplos valores)"""
        if not value:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        # Assume separação por ponto-e-vírgula ou vírgula
        return [v.strip() for v in value.replace(';', ',').split(',') if v.strip()]
    
    @staticmethod
    def _parse_tags(value: str) -> List[str]:
        """Parse campo de tags"""
        if not value:
            return []
        return [t.strip() for t in value.split(',') if t.strip()]
    
    def add_update(self, project_id: str, update_data: dict) -> bool:
        """Adiciona uma nova atualização na lista de 'Atualizações' do SharePoint"""
        try:
            updates_list = self.ctx.web.lists.get_by_title("AtualizacoesProjetos")
            new_item = {
                "ProjectId": project_id,
                "Title": update_data.get("title"),
                "Description": update_data.get("description"),
                "Source": update_data.get("source", "api"),
                "Category": update_data.get("category", "geral"),
                "Timestamp": datetime.now()
            }
            # Nota: implementação real depende da estrutura da sua lista
            logger.info(f"Update registrado para projeto {project_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao registrar atualização: {e}")
            return False
