import azure.functions as func
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from src.data.sharepoint_client import SharePointClient
from src.logic.deadline_checker import DeadlineChecker
from src.integrations.notifier import Notifier

# Carregar variáveis de ambiente locais
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(mytimer: func.TimerRequest) -> None:
    """
    Azure Function com Timer Trigger
    Executa diariamente às 8h para verificar prazos de projetos
    """
    logger.info(f"Iniciando verificação de prazos - {datetime.now()}")
    
    if mytimer and not mytimer.past_due:
        logger.info("Timer trigger executando no horário correto")
    
    try:
        # 1. Carregar projetos do SharePoint
        logger.info("Conectando ao SharePoint...")
        sp_client = SharePointClient.from_env()
        projects = sp_client.load_projects(list_name=os.getenv("SHAREPOINT_LIST_NAME", "ProjetosCGIN"))
        logger.info(f"{len(projects)} projetos carregados")
        
        if not projects:
            logger.warning("Nenhum projeto encontrado - verificando configuração")
            return
        
        # 2. Verificar prazos e gerar alertas
        logger.info("Verificando prazos...")
        checker = DeadlineChecker()
        result = checker.batch_check(projects)
        
        logger.info(f"Verificação concluída: {len(result['all_alerts'])} alertas gerados")
        logger.info(f"Projetos em risco: {result['projects_at_risk']}/{result['total_projects']}")
        
        # 3. Enviar alertas se houver
        if result['all_alerts']:
            logger.info("Enviando alertas...")
            notifier = Notifier()
            send_result = notifier.send_alerts(result['all_alerts'], projects)
            logger.info(f"Envio de alertas: {send_result}")
        else:
            logger.info("✅ Nenhum alerta crítico - todos os prazos em dia!")
        
        # 4. (Opcional) Registrar log de execução em storage
        # _log_execution_result(result)
        
        logger.info("✅ Processamento concluído com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro crítico no processamento: {str(e)}", exc_info=True)
        # Em produção: enviar alerta de falha do sistema para admin
        raise

def _log_execution_result(result: dict):
    """Registra resultado da execução em Azure Table Storage (opcional)"""
    # Implementação futura: usar Azure CosmosDB ou Table Storage
    # para histórico de execuções e auditoria
    pass
