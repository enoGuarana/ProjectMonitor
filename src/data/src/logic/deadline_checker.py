from datetime import date
from typing import List, Tuple
from src.data.models import Project, Milestone, ProjectStatus

class DeadlineChecker:
    """Responsável por calcular status de prazos e gerar alertas"""
    
    # Configurações de thresholds para alertas
    ALERT_THRESHOLDS = {
        'milestone': [30, 15, 7, 3],  # dias antes do marco
        'project_deadline': [60, 30, 15, 7]  # dias antes do vencimento do projeto
    }
    
    @classmethod
    def check_project(cls, project: Project) -> List[dict]:
        """
        Verifica um projeto e retorna lista de alertas pertinentes
        Retorna: [{"type": str, "target": str, "days": int, "severity": str, "message": str}]
        """
        alerts = []
        today = date.today()
        
        # 1. Verificar prazo final do projeto
        if project.status != ProjectStatus.CONCLUIDO and project.days_until_deadline is not None:
            days = project.days_until_deadline
            for threshold in cls.ALERT_THRESHOLDS['project_deadline']:
                if days == threshold:
                    alerts.append({
                        'type': 'project_deadline',
                        'target': project.name,
                        'days': days,
                        'severity': cls._calculate_severity(days, 'project'),
                        'message': f"Projeto '{project.name}' vence em {days} dias ({project.expected_end_date})"
                    })
                    break  # evita múltiplos alertas para o mesmo projeto
        
        # 2. Verificar marcos (milestones)
        for milestone in project.milestones:
            if milestone.status == "concluido" or milestone.actual_date:
                continue  # pular marcos já concluídos
            
            days = milestone.days_until
            if days is None:
                continue
                
            # Marco atrasado
            if days < 0:
                alerts.append({
                    'type': 'milestone_overdue',
                    'target': f"{project.name} > {milestone.title}",
                    'days': abs(days),
                    'severity': 'CRITICO',
                    'message': f"⚠️ MARCO ATRASADO: '{milestone.title}' estava para {milestone.expected_date} ({abs(days)} dias de atraso)"
                })
            else:
                # Alerta de aproximação
                for threshold in cls.ALERT_THRESHOLDS['milestone']:
                    if days == threshold:
                        alerts.append({
                            'type': 'milestone_approaching',
                            'target': f"{project.name} > {milestone.title}",
                            'days': days,
                            'severity': cls._calculate_severity(days, 'milestone'),
                            'message': f"Marco '{milestone.title}' em {project.name} vence em {days} dias"
                        })
                        break
        
        return alerts
    
    @staticmethod
    def _calculate_severity(days: int, alert_type: str) -> str:
        """Calcula severidade baseada em dias restantes e tipo de alerta"""
        thresholds = DeadlineChecker.ALERT_THRESHOLDS.get(alert_type, [30, 15, 7])
        if days <= 7:
            return "CRITICO"
        elif days <= 15:
            return "ALTO"
        elif days <= 30:
            return "MEDIO"
        return "BAIXO"
    
    @classmethod
    def batch_check(cls, projects: List[Project]) -> dict:
        """
        Verifica múltiplos projetos e retorna estrutura consolidada
        Retorna: {
            'total_projects': int,
            'projects_at_risk': int,
            'alerts_by_severity': {'CRITICO': [], 'ALTO': [], ...},
            'all_alerts': List[dict]
        }
        """
        all_alerts = []
        risk_count = 0
        
        for project in projects:
            alerts = cls.check_project(project)
            if alerts or project.is_at_risk:
                risk_count += 1
            all_alerts.extend(alerts)
        
        # Agrupar por severidade
        by_severity = {'CRITICO': [], 'ALTO': [], 'MEDIO': [], 'BAIXO': []}
        for alert in all_alerts:
            by_severity[alert['severity']].append(alert)
        
        return {
            'total_projects': len(projects),
            'projects_at_risk': risk_count,
            'alerts_by_severity': by_severity,
            'all_alerts': all_alerts,
            'generated_at': date.today().isoformat()
        }
