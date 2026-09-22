from ..extensions import db


class Coach(db.Model):
    __tablename__ = "coaches"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"))
    name_ar = db.Column(db.String(180), nullable=False)
    sport_id = db.Column(db.Integer, db.ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False)
    hourly_rate = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    bio_ar = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class TrainingProgram(db.Model):
    __tablename__ = "training_programs"
    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey("coaches.id", ondelete="RESTRICT"))
    name_ar = db.Column(db.String(180), nullable=False)
    description_ar = db.Column(db.Text)
    capacity = db.Column(db.Integer)
    price = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Lesson(db.Model):
    __tablename__ = "training_lessons"
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("training_programs.id", ondelete="RESTRICT"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id", ondelete="RESTRICT"))
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="scheduled")
