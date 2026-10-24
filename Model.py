from pydantic import BaseModel, Field
from sqlalchemy import select,func,DateTime
from sqlalchemy.orm import Session
from DatabaseModel import Readings,AppSession,FanEvent
from fastapi import Depends
# config import 
from config import get_session
from datetime import datetime



class Reading(BaseModel):
    temp: float
    humidity: float


def get_latest_reading(db) -> Reading | None:
    row = db.query(Readings).filter(
        Readings.session_id == db.query(AppSession.id).order_by(AppSession.created_at.desc()).limit(1).scalar()
    ).order_by(
        Readings.recieved_at.desc()  # <-- Changed from created_at to recieved_at
    ).limit(1).first()

    if row is None:
        return None
    # Numeric columns come back as Decimal, so convert to float
    return Reading(temp=float(row.temperature), humidity=float(row.humidity))


class Fan(BaseModel):
    status: bool = False
    speed: float = Field(default=0, ge=0, le=100)
    threshold: float = 30 # temperature at which fan turns on
    max_temp: float = 40 # temp at which fan is at max speed 
    min_speed: float = 30

    def _effective_threshold(self, reading: Reading) -> float:
        if reading.humidity > 70:
            return self.threshold - 2
        return self.threshold

    def set_status(self, reading: Reading) -> bool:
        self.status = reading.temp >= self._effective_threshold(reading)
        if not self.status:
            self.speed = 0
        return self.status

    def set_speed(self, reading: Reading) -> float:
        if not self.status:
            self.speed = 0
            return self.speed

        low = self._effective_threshold(reading)
        span = self.max_temp - low

        if span > 0:
            ratio = (reading.temp - low) / span
        else:
            ratio = 1
        ratio = min(max(ratio, 0), 1)

        self.speed = round(self.min_speed + ratio * (100 - self.min_speed), 1)
        return self.speed

    def update(self, db) -> "Fan":
        reading = get_latest_reading(db)
        if reading is None:
            return self
        self.set_status(reading)
        self.set_speed(reading)
        return self
    
    def record_fan_event(self, db):
        session = db.query(AppSession).order_by(AppSession.created_at.desc()).first()
        if session is None:
            return

        last = (
            db.query(FanEvent.status)
            .filter(FanEvent.session_id == session.id)
            .order_by(FanEvent.changed_at.desc())
            .first()
        )
        was_on = last.status if last is not None else False

        if self.status != was_on:
            db.add(FanEvent(session_id=session.id, status=self.status, changed_at=datetime.now()))
            db.commit()



    def on_off_pairs(self,session_id,db): # for us to get the runtime we need to add the time duration between consective
        #on off pairs so this gives us the on off pairs Lead is a func thiat gives the next value
#Pair every row with the next one. LEAD gives each row the time of the row after it. That produces on→off pairs and off→on pairs.
# Keep only the rows where the fan turned on. That removes the off→on pairs, which are the periods when the fan was off. Only the on→off pairs remain, and those are the periods it was running.
        off_time = func.lead(FanEvent.changed_at, type_=DateTime).over(order_by=FanEvent.changed_at)

        sub = (
            select(FanEvent.status, FanEvent.changed_at.label("on_time"), off_time.label("off_time"))
            .where(FanEvent.session_id == session_id)
            .subquery()
        )

        return db.execute(
            select(sub.c.on_time, sub.c.off_time)
            .where(sub.c.status.is_(True)) # this gives all on-> off pairs
            .order_by(sub.c.on_time)
        ).all()
    
    def fan_runtime(self, session_id, db: Session) -> float:
            now = datetime.now() 
            
            total = 0.0
           
            for on_time, off_time in self.on_off_pairs(session_id, db):
                total += ((off_time or now) - on_time).total_seconds()
            return total

    

    
        
        


class FanOutput(BaseModel):
    status: bool
    speed: float=Field(default=0, ge=0, le=100)

class Trend: # for the thrends made a sepearate class
    def __init__(self, current: float, speed: float):
        self.current = current
        self.speed = speed          # degrees per minute(name is bad it is kind of rate of change rather then just speed)

    @classmethod
    def Trend_of_n_rows(cls, db, n=10):
        # 1. Get the latest session ID
        latest_session_id = db.query(AppSession.id).order_by(AppSession.created_at.desc()).limit(1).scalar()
        
        # 2. Filter readings by that session
        rows = (
            db.query(Readings)
            .filter(Readings.session_id == latest_session_id)
            .order_by(Readings.recieved_at.desc())
            .limit(n)
            .all()
        )
        
        if len(rows) < 2:
            return None
        rows.reverse()  # oldest first
        minutes = (rows[-1].recieved_at - rows[0].recieved_at).total_seconds() / 60
        if minutes <= 0:
            return None
        current = float(rows[-1].temperature)
        speed = (current - float(rows[0].temperature)) / minutes
        return cls(current, speed)

    def temp_in(self, minutes: float) -> float: #This tells temp in 'N' minutes
        return self.current + self.speed * minutes

    def will_reach(self, target: float, within_minutes: float = 30) -> dict: #This tells stats about when i target will be reached within a time period ('within_minutes')
        if abs(target - self.current) < 0.1:
            minutes_unti_target = 0
        elif (target - self.current) * self.speed > 0:   # moving toward the target
            minutes_unti_target = (target - self.current) / self.speed
        else:
            minutes_unti_target = None

        return {
            "current": self.current,
            "target": target,
            "speed_per_min": round(self.speed, 3),
            "minutes_to_target": round(minutes_unti_target, 1) if minutes_unti_target is not None else None,
            "will_reach": minutes_unti_target is not None and minutes_unti_target <= within_minutes,
        }

