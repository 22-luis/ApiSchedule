import uuid
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.organization.models.team import Team, UserTeam
from app.modules.organization.repositories import team_repository, user_repository
from app.modules.organization.schemas.team import TeamOut, TeamMemberOut

class TeamService:
    @staticmethod
    def _build_team_out(db: Session, team: Team, target_date: date) -> TeamOut:
        active_members_map = {}
        for association in team.member_associations:
            if association.start_date <= target_date and (
                    association.end_date is None or association.end_date >= target_date):
                if association.user_id not in active_members_map:
                    active_members_map[association.user_id] = TeamMemberOut(
                        userId=association.user_id,
                        username=association.user.username if association.user else None,
                        fullName=association.user.full_name if association.user else None,
                        startDate=association.start_date,
                        endDate=association.end_date
                    )

        supervisor = user_repository.find_by_id(db, team.supervisorId)

        return TeamOut(
            id=team.id,
            name=team.name,
            supervisorId=team.supervisorId,
            supervisorUsername=supervisor.username if supervisor else None,
            members=list(active_members_map.values())
        )

    @staticmethod
    def get_all_teams(db: Session, target_date: date):
        teams = team_repository.find_all_teams(db)
        return [TeamService._build_team_out(db, team, target_date) for team in teams]

    @staticmethod
    def create_team(db: Session, team_in):
        team = Team(
            name=team_in.name,
            supervisorId=team_in.supervisorId
        )
        team_repository.save_team(db, team)
        
        today = date.today()
        if team_in.members:
            for member_config in team_in.members:
                user_team = UserTeam(
                    user_id=member_config.userId,
                    team_id=team.id,
                    start_date=member_config.startDate or today,
                    end_date=member_config.endDate
                )
                team_repository.add_association(db, user_team)
            db.refresh(team)

        return TeamService._build_team_out(db, team, today)

    @staticmethod
    def update_team_members(db: Session, team_id: uuid.UUID, update_data):
        team = team_repository.find_team_by_id(db, team_id)
        if not team:
            return None
            
        target_date = update_data.date
        new_member_ids = set(update_data.userIds)
        
        current_associations = []
        for assoc in team.member_associations:
            if assoc.start_date <= target_date and (assoc.end_date is None or assoc.end_date >= target_date):
                current_associations.append(assoc)
                
        current_member_ids = {assoc.user_id for assoc in current_associations}
        
        for assoc in current_associations:
            if assoc.user_id not in new_member_ids:
                end_date = target_date - timedelta(days=1)
                if assoc.start_date > end_date:
                    team_repository.delete_association(db, assoc)
                else:
                    assoc.end_date = end_date
                    
        for user_id in new_member_ids:
            if user_id not in current_member_ids:
                new_assoc = UserTeam(
                    user_id=user_id,
                    team_id=team.id,
                    start_date=target_date,
                    end_date=None
                )
                team_repository.add_association(db, new_assoc)
                
        db.commit()
        db.refresh(team)
        return TeamService._build_team_out(db, team, target_date)

    @staticmethod
    def update_team(db: Session, team_id: uuid.UUID, team_update, target_date: date):
        team = team_repository.find_team_by_id(db, team_id)
        if not team:
            return None
        
        if team_update.name is not None:
            team.name = team_update.name
        if team_update.supervisorId is not None:
            team.supervisorId = team_update.supervisorId
            
        db.commit()
        db.refresh(team)
        return TeamService._build_team_out(db, team, target_date)

    @staticmethod
    def delete_team(db: Session, team_id: uuid.UUID):
        team = team_repository.find_team_by_id(db, team_id)
        if not team:
            return False
        
        team_repository.delete_team(db, team)
        return True
