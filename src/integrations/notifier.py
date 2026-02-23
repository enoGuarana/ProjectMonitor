import os
import json
import logging
import requests
from typing import List
from src.data.models import Project

logger = logging.getLogger(__name__)

class Notifier:
    """Envia alertas para canais configurados (Teams, Email)"""
    
    def __init__(self, teams_webhook: str = None):
        self.teams_webhook = teams_webhook or os.getenv("TEAMS_WEBHOOK_URL")
    
    def send_alerts(self, alerts: List[dict], projects: List[Project]) -> dict:
        """
        Envia alertas consolidados
        Retorna: {"sent": int, "failed": int, "errors": List[str]}
        """
        if not alerts:
            logger.info("Nenhum alerta para enviar")
            return {"sent": 0, "failed": 0, "errors": []}
        
        results = {"sent": 0, "failed": 0, "errors": []}
        
        # Agrupar alertas por projeto para evitar spam
        alerts_by_project = {}
        for alert in alerts:
            proj_name = alert.get('target', 'Desconhecido').split(' > ')[0]
            if proj_name not in alerts_by_project:
                alerts_by_project[proj_name] = []
            alerts_by_project[proj_name].append(alert)
        
        # Enviar mensagem consolidada para Teams
        if self.teams_webhook:
            try:
                message = self._format_teams_message(alerts_by_project, projects)
                response = requests.post(
                    self.teams_webhook,
                    json=message,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                if response.status_code == 200:
                    results["sent"] += len(alerts)
                    logger.info(f"Alertas enviados para Teams: {len(alerts)} notificações")
                else:
                    results["failed"] += len(alerts)
                    results["errors"].append(f"Teams API: {response.status_code} - {response.text}")
            except Exception as e:
                results["failed"] += len(alerts)
                results["errors"].append(f"Erro ao enviar para Teams: {str(e)}")
        else:
            logger.warning("TEAMS_WEBHOOK_URL não configurado - alertas não enviados")
            results["failed"] = len(alerts)
            results["errors"].append("Webhook do Teams não configurado")
        
        # TODO: Implementar envio por email via Microsoft Graph
        # (pode ser adicionado como próximo passo)
        
        return results
    
    def _format_teams_message(self, alerts_by_project: dict, projects: List[Project]) -> dict:
        """Formata mensagem no formato Adaptive Cards do Microsoft Teams"""
        
        # Criar seção para cada projeto com alertas
        sections = []
        for proj_name, alerts in alerts_by_project.items():
            # Encontrar projeto completo para pegar responsáveis
            project = next((p for p in projects if p.name == proj_name), None)
            responsible = ", ".join(project.responsible_team) if project else "Não informado"
            
            alert_items = []
            for alert in alerts:
                emoji = "🔴" if alert['severity'] == 'CRITICO' else "🟡" if alert['severity'] == 'ALTO' else "🔵"
                alert_items.append({
                    "type": "TextBlock",
                    "text": f"{emoji} {alert['message']}",
                    "wrap": True,
                    "size": "Small"
                })
            
            sections.append({
                "type": "Container",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"📁 {proj_name}",
                        "weight": "Bolder",
                        "size": "Medium",
                        "color": "Accent"
                    },
                    {
                        "type": "TextBlock",
                        "text": f"Responsável: {responsible}",
                        "size": "Small",
                        "isSubtle": True
                    }
                ] + alert_items,
                "style": "emphasis",
                "separator": True
            })
        
        # Montar Adaptive Card completo
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "🚨 Alertas de Prazos - Project Monitor",
                                "size": "Large",
                                "weight": "Bolder",
                                "color": "Attention"
                            },
                            {
                                "type": "TextBlock",
                                "text": f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                                "size": "Small",
                                "isSubtle": True
                            }
                        ] + sections,
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "Ver Dashboard",
                                "url": os.getenv("POWERBI_DASHBOARD_URL", "#")
                            }
                        ]
                    }
                }
            ]
        }
