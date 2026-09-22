from datetime import datetime, timezone
from ..extensions import db


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(180), nullable=False)
    short_name = db.Column(db.String(50))
    logo_url = db.Column(db.String(500))
    captain_player_id = db.Column(db.Integer, db.ForeignKey("players.id", ondelete="SET NULL"))
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"))
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Player(db.Model):
    __tablename__ = "players"
    id = db.Column(db.Integer, primary_key=True)
    player_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(180), nullable=False, index=True)
    phone = db.Column(db.String(40), index=True)
    photo_url = db.Column(db.String(500))
    birth_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class TeamPlayer(db.Model):
    __tablename__ = "team_players"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    jersey_number = db.Column(db.Integer)
    joined_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    left_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(30), nullable=False, default="active")
