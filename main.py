# fastapi imports
from fastapi import FastAPI,Depends,HTTPException
from config import get_session,engine
from sqlalchemy.orm import Session
from Model import Fan,FanOutput,Trend,AppSession
from DatabaseModel import Base,Readings
from sqlalchemy import func
from pydantic import BaseModel
from Assistant import run_assistant



app = FastAPI()
Base.metadata.create_all(bind=engine)


@app.get("/")
def greet():
    return {"message": "Salam bachi"}

@app.post("/evaluate",response_model=FanOutput)
def evaluate(db: Session = Depends(get_session)):
    fan = Fan()
    fan.update(db)
    fan.record_fan_event(db)
    return fan

@app.post('/will_reach')
def reach(target_temp: float, within_minutes: float = 30,db:Session=Depends(get_session)):
    trend=Trend.Trend_of_n_rows(db)
    if trend is None:
        return HTTPException(status_code=404,detail="Not enough Readings")
    
    return trend.will_reach(target_temp,within_minutes=within_minutes)

@app.post('/temp_in_minutes')
def temp_in_minutes(minutes: float,db:Session=Depends(get_session)):
    trend=Trend.Trend_of_n_rows(db)
    if trend is None:
        raise  HTTPException(status_code=404,detail="Not enough Readings")
    return trend.temp_in(minutes=minutes)

@app.get('/reports')
def report(db: Session = Depends(get_session)):
    session = db.query(AppSession).order_by(AppSession.created_at.desc()).first()
    if session is None:
        raise HTTPException(status_code=404, detail="No session found")

    avg_t, max_t, min_t = db.query(
        func.avg(Readings.temperature),
        func.max(Readings.temperature),
        func.min(Readings.temperature),
    ).filter(Readings.session_id == session.id).one()

    seconds = Fan().fan_runtime(session.id, db)

    return {
        "avg_temperature": round(float(avg_t), 1) if avg_t is not None else None,
        "max_temperature": float(max_t) if max_t is not None else None,
        "min_temperature": float(min_t) if min_t is not None else None,
        "fan_runtime_seconds": round(seconds),
        "fan_runtime": f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m",
    }

    
class ChatIn(BaseModel):
    message: str
    history: list[dict] = []

@app.post("/assistant")
def assistant_route(body: ChatIn, db: Session = Depends(get_session)):
    try:
        return {"reply": run_assistant(db, body.message, body.history)}
    except Exception as e:
        print("Assistant error:", e)
        raise HTTPException(status_code=503, detail="Assistant unavailable")


@app.get('/check_alert')
def check_alert(db: Session = Depends(get_session)):
    reading = Readings.get_latest_reading(db)
    if reading is None:
        raise HTTPException(status_code=404, detail="No readings found")
    
    CRITICAL_TEMP = 35.0  # Set your danger threshold here
    
    if reading.temp >= CRITICAL_TEMP:
        # Trigger physical server-side audio beep
        try:
            import winsound
            winsound.Beep(1000, 1500)  # 1000Hz frequency for 1.5 seconds
        except ImportError:
            pass # Failsafe in case of OS changes later
            
        return {
            "alert": True,
            "message": f"CRITICAL ALERT: Temperature reached {reading.temp}°C!",
            "temperature": reading.temp
        }
        
    return {
        "alert": False,
        "message": "Temperature is within safe limits.",
        "temperature": reading.temp
    }
    

