from datetime import datetime, timezone
from ..extensions import db


class Tournament(db.Model):
    __tablename__ = "tournaments"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(220), nullable=False)
    sport_id = db.Column(db.Integer, db.ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False)
    starts_on = db.Column(db.Date, nullable=False)
    ends_on = db.Column(db.Date)
    registration_open = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(30), nullable=False, default="draft")
    entry_fee = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    prize_description_ar = db.Column(db.Text)
    rules_ar = db.Column(db.Text)


class TournamentRegistration(db.Model):
    __tablename__ = "tournament_registrations"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="RESTRICT"))
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"))
    status = db.Column(db.String(30), nullable=False, default="pending")
    registered_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class TournamentGroup(db.Model):
    __tablename__ = "tournament_groups"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    name_ar = db.Column(db.String(80), nullable=False)


class TournamentRound(db.Model):
    __tablename__ = "tournament_rounds"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    name_ar = db.Column(db.String(120), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey("tournament_rounds.id", ondelete="SET NULL"))
    group_id = db.Column(db.Integer, db.ForeignKey("tournament_groups.id", ondelete="SET NULL"))
    team_a_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL"))
    team_b_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="SET NULL"))
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id", ondelete="SET NULL"))
    starts_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(30), nullable=False, default="scheduled")
    score_a = db.Column(db.Integer)
    score_b = db.Column(db.Integer)


class MatchEvent(db.Model):
    __tablename__ = "match_events"
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id", ondelete="SET NULL"))
    event_type = db.Column(db.String(40), nullable=False)
    minute = db.Column(db.Integer)
    description_ar = db.Column(db.String(300))
