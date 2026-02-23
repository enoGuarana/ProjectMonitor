import pytest
from datetime import date, timedelta
from src.data.models import Project, Milestone, ProjectStatus
from src.logic.deadline_checker import DeadlineChecker

@pytest.fixture
def sample_project():
    return Project(
        id="PROJ-001",
        name="Modernização Sistema X",
        area_responsavel="CGIN",
        responsible_team=["team@cgim.gov.br"],
        start_date=date.today() - timedelta(days=30),
        expected_end_date=date.today() + timedelta(days=20),
        milestones=[
            Milestone(
                id="M1",
                title="Levantamento de requisitos",
                expected_date=date.today() - timedelta(days=5),  # atrasado!
                status="pendente"
            ),
            Milestone(
                id="M2", 
                title="Desenvolvimento MVP",
                expected_date=date.today() + timedelta(days=7),  # alerta em 7 dias
                status="pendente"
            )
        ]
    )

def test_check_project_detects_overdue_milestone(sample_project):
    alerts = DeadlineChecker.check_project(sample_project)
    
    overdue_alerts = [a for a in alerts if a['type'] == 'milestone_overdue']
    assert len(overdue_alerts) == 1
    assert overdue_alerts[0]['severity'] == 'CRITICO'
    assert "atrasado" in overdue_alerts[0]['message'].lower()

def test_check_project_detects_approaching_deadline(sample_project):
    # Ajustar projeto para ter marco em 7 dias
    sample_project.milestones[1].expected_date = date.today() + timedelta(days=7)
    
    alerts = DeadlineChecker.check_project(sample_project)
    approaching = [a for a in alerts if a['type'] == 'milestone_approaching']
    
    assert len(approaching) >= 1
    assert approaching[0]['days'] == 7

def test_batch_check_aggregates_correctly(sample_project):
    projects = [sample_project]
    result = DeadlineChecker.batch_check(projects)
    
    assert result['total_projects'] == 1
    assert result['projects_at_risk'] == 1
    assert 'CRITICO' in result['alerts_by_severity']
    assert len(result['all_alerts']) > 0

def test_concluded_project_generates_no_alerts():
    project = Project(
        id="PROJ-DONE",
        name="Projeto Concluído",
        area_responsavel="CGIN",
        responsible_team=["team@cgim.gov.br"],
        start_date=date(2024, 1, 1),
        expected_end_date=date(2024, 6, 1),  # já passou
        status=ProjectStatus.CONCLUIDO
    )
    
    alerts = DeadlineChecker.check_project(project)
    assert len(alerts) == 0  # projetos concluídos não geram alertas
