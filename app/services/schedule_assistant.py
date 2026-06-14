"""Conversational Schedule Assistant — intelligente Terminplanung mit Verfügbarkeitsdaten."""
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.models import Person, Ausschuss, Mitgliedschaft, Verfuegbarkeit, PlannedMeeting, Urlaub
from app.models.enums import AusschussTyp, Wochentag, Rolle
from app.services.meeting_pattern_analyzer import MeetingPatternAnalyzer

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class UserRole(str, Enum):
    BUERGERMEISTER = "bm"
    OBMANN = "ob"


class MeetingType(str, Enum):
    STR = "str"   # Stadtratsitzung
    GR = "gr"     # Gemeinderatsitzung
    AUSSCHUSS = "ausschuss"


@dataclass
class Message:
    role: MessageRole
    content: str


@dataclass
class ConversationState:
    user_role: UserRole | None = None
    meeting_type: MeetingType | None = None
    selected_ausschuss: str | None = None
    main_meeting_selected: bool = False
    selected_ausschuesse: list[str] = None
    main_meeting_date: date | None = None
    main_meeting_time: str | None = None
    suggested_meetings: list[tuple[date, str, int]] = None  # Top-5 Vorschläge: (date, time, score)
    ausschuss_meetings: dict[str, tuple[date, str, int]] = None  # {name: (date, time, score)}
    messages: list[Message] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.selected_ausschuesse is None:
            self.selected_ausschuesse = []
        if self.suggested_meetings is None:
            self.suggested_meetings = []
        if self.ausschuss_meetings is None:
            self.ausschuss_meetings = {}


class ScheduleAssistant:
    """Intelligente Terminplanung mit Verfügbarkeitsdaten aus DB."""

    # Constraints (NÖ Gemeindeordnung 1973)
    MIN_DAYS_STR = 60    # Stadtratsitzung: min. 2 Monate
    MIN_DAYS_GR = 90     # Gemeinderatsitzung: min. 3 Monate
    DAYS_BEFORE_AUSSCHUSS = (7, 14)

    MEETING_SLOTS = ["09:00", "10:00", "14:00", "15:00", "18:00", "19:30"]
    DAY_MAPPING = {0: Wochentag.MO, 1: Wochentag.DI, 2: Wochentag.MI,
                   3: Wochentag.DO, 4: Wochentag.FR}

    def __init__(self, db: Session = None):
        self.state = ConversationState()
        self.db = db

    def process_user_input(self, user_message: str) -> str:
        """Hauptlogik: Input → Klassifizierung → Response."""
        msg_clean = user_message.strip().lower()
        self.state.messages.append(Message(MessageRole.USER, user_message))

        # 1. Erkenne Rolle
        if self.state.user_role is None:
            return self._recognize_role(msg_clean)

        # 2. Erkenne Sitzungstyp
        if self.state.meeting_type is None:
            return self._recognize_meeting_type(msg_clean)

        # 3. Verarbeite Haupttermin-Auswahl
        if not self.state.main_meeting_selected:
            return self._process_selection(msg_clean)

        # 4. (Optional für BM) Frage nach Ausschüssen für vorbereitende Sitzungen
        if self.state.user_role == UserRole.BUERGERMEISTER and not self.state.selected_ausschuesse:
            return self._ask_ausschuesse_for_main_meeting(msg_clean)

        # 5. Alle Schritte abgeschlossen — Fallback-Antwort statt None.
        #    Verhindert, dass die API None erhält und einen 500er wirft.
        response = (
            "✅ **Die Planung ist abgeschlossen.**\n\n"
            "Möchten Sie eine neue Planung starten? Nutzen Sie dazu **/reset**."
        )
        self._add_response(response)
        return response

    def _recognize_role(self, msg: str) -> str:
        """Erkenne BM oder OB."""
        if any(x in msg for x in ["bm", "bürgermeister", "bürgerm"]):
            self.state.user_role = UserRole.BUERGERMEISTER
            response = "👋 Willkommen **Bürgermeister**!\n\nWas möchten Sie planen?\n• **STR** = Stadtratsitzung (alle 2 Monate)\n• **GR** = Gemeinderatsitzung (alle 3 Monate)"
        elif any(x in msg for x in ["ob", "obmann"]):
            self.state.user_role = UserRole.OBMANN
            response = "👋 Willkommen **Obmann**!\n\nWelcher Ausschuss? (z.B. 'Infrastruktur', 'Bildung', 'Sport'...)"
        else:
            response = "❓ Bitte antworte mit:\n• **BM** = Bürgermeister\n• **OB** = Obmann"

        self._add_response(response)
        return response

    def _recognize_meeting_type(self, msg: str) -> str:
        """Erkenne STR, GR oder Ausschussname."""
        if self.state.user_role != UserRole.BUERGERMEISTER:
            # Für OB: Input ist Ausschussname
            self.state.selected_ausschuss = msg
            self.state.meeting_type = MeetingType.AUSSCHUSS
            return self._suggest_ausschuss_dates()

        if any(x in msg for x in ["str", "stadtrat", "stadtratsitzung"]):
            self.state.meeting_type = MeetingType.STR
            return self._suggest_dates(MeetingType.STR)
        elif any(x in msg for x in ["gr", "gemeinderat", "gemeinderatsitzung"]):
            self.state.meeting_type = MeetingType.GR
            return self._suggest_dates(MeetingType.GR)
        else:
            response = "❓ Bitte antworte mit:\n• **STR** = Stadtratsitzung\n• **GR** = Gemeinderatsitzung"
            self._add_response(response)
            return response

    def _get_participants(self, mtype: MeetingType) -> list[Person]:
        """Hole alle Teilnehmer für STR/GR/Ausschuss."""
        if not self.db:
            return []

        if mtype == MeetingType.STR:
            # Alle aktiven Stadträte (Gremium = "Stadtrat")
            stmt = select(Person).where(
                (Person.aktiv == True) &
                (Person.gremium.contains("Stadtrat"))
            )
        elif mtype == MeetingType.GR:
            # Alle aktiven Gemeinde/Stadträte
            stmt = select(Person).where(Person.aktiv == True)
        else:  # AUSSCHUSS
            # Mitglieder des Ausschusses
            ausschuss = self.db.query(Ausschuss).filter(
                Ausschuss.name.ilike(f"%{self.state.selected_ausschuss}%")
            ).first()
            if not ausschuss:
                return []
            person_ids = [m.person_id for m in ausschuss.mitgliedschaften if m.person]
            stmt = select(Person).where(Person.id.in_(person_ids))

        return self.db.scalars(stmt).all()

    def _get_availability_score(self, persons: list[Person], dt: date, time_str: str) -> int:
        """Berechne Verfügbarkeitsscore für Termin (0-100)."""
        if not persons or not self.db:
            return 75  # Fallback

        time_hour = int(time_str.split(":")[0])
        wochentag = self.DAY_MAPPING.get(dt.weekday(), Wochentag.MO)

        available_count = 0
        for person in persons:
            # Suche Verfügbarkeit
            stmt = select(Verfuegbarkeit).where(
                (Verfuegbarkeit.person_id == person.id) &
                (Verfuegbarkeit.wochentag == wochentag) &
                (Verfuegbarkeit.stunde == time_hour) &
                (Verfuegbarkeit.verfuegbar == True)
            )
            if self.db.scalars(stmt).first():
                available_count += 1

        score = int((available_count / len(persons)) * 100) if persons else 0
        return max(50, score)  # Min. 50% für optionale Vorschläge

    def _suggest_dates(self, mtype: MeetingType) -> str:
        """Generiere intelligente Terminvorschläge mit Verfügbarkeitsprüfung."""
        participants = self._get_participants(mtype)

        if not participants:
            response = "⚠️ Keine Teilnehmer gefunden. Bitte überprüfen Sie die Ausschuss-Mitgliedschaften."
            self._add_response(response)
            return response

        # Sammle verfügbare Zeitslots pro Wochentag
        available_slots = self._get_available_slots_per_weekday(participants)

        # Nutze MeetingPatternAnalyzer für intelligente Vorschläge
        analyzer = MeetingPatternAnalyzer(db=self.db)
        suggestions = analyzer.suggest_next_meetings(
            mtype.value.upper(), count=5, persons=participants, db=self.db, available_slots=available_slots
        )

        if not suggestions:
            response = "⚠️ Keine passenden Termine gefunden. Bitte prüfen Sie die Verfügbarkeiten und Urlaube."
            self._add_response(response)
            return response

        # Speichere die Top-5 für die spätere Auswahl in _process_selection
        self.state.suggested_meetings = list(suggestions[:5])

        mtype_name = "Stadtratsitzung" if mtype == MeetingType.STR else "Gemeinderatsitzung"
        response = f"📅 **Top 5 Vorschläge für {mtype_name}:**\n*(Historische Muster + Verfügbarkeiten)*\n\n"

        for i, (dt, time, score) in enumerate(self.state.suggested_meetings, 1):
            wochentag = ["Mo", "Di", "Mi", "Do", "Fr"][dt.weekday()]
            response += f"{i}. {wochentag} {dt.strftime('%d.%m.%Y')} **{time}** ({score}% OK)\n"

        response += "\n💡 *Basierend auf: Historischen Terminen + Verfügbarkeitslisten + Urlaubsdaten*"
        response += (
            "\n\n💡 **Optionen:**"
            "\n- Geben Sie **1-5** ein (Top-Vorschlag)"
            "\n- Oder **Uhrzeit** (z.B. 16:00)"
            "\n- Oder **Datum** (z.B. 25.06.2026)"
        )
        self._add_response(response)
        return response

    def _get_available_slots_per_weekday(self, persons: list[Person]) -> dict[int, list[int]]:
        """Sammle verfügbare Zeitslots pro Wochentag für alle Personen."""
        available_slots = {0: [], 1: [], 2: [], 3: [], 4: []}  # Mo-Fr

        if not self.db:
            # Fallback
            return {0: [14, 15, 18], 1: [14, 15, 18], 2: [14, 15, 18], 3: [14, 15, 18], 4: []}

        for person in persons:
            stmt = select(Verfuegbarkeit).where(
                (Verfuegbarkeit.person_id == person.id) &
                (Verfuegbarkeit.verfuegbar == True)
            )
            verfuegbarkeiten = self.db.scalars(stmt).all()

            for v in verfuegbarkeiten:
                weekday_map = {Wochentag.MO: 0, Wochentag.DI: 1, Wochentag.MI: 2, Wochentag.DO: 3, Wochentag.FR: 4}
                weekday = weekday_map.get(v.wochentag)
                if weekday is not None and v.stunde not in available_slots[weekday]:
                    available_slots[weekday].append(v.stunde)

        # Nur Stunden behalten, die für ALLE Personen verfügbar sind
        for weekday in available_slots:
            if available_slots[weekday]:
                common_hours = set(available_slots[weekday])
                for person in persons:
                    stmt = select(Verfuegbarkeit).where(
                        (Verfuegbarkeit.person_id == person.id) &
                        (Verfuegbarkeit.verfuegbar == True)
                    )
                    person_hours = {v.stunde for v in self.db.scalars(stmt).all()}
                    common_hours &= person_hours

                available_slots[weekday] = sorted(list(common_hours)) if common_hours else []

        return available_slots

    def _suggest_ausschuss_dates(self) -> str:
        """Für OB: Ausschuss-Termine nächste 2 Wochen."""
        participants = self._get_participants(MeetingType.AUSSCHUSS)

        # Lade echte Verfügbarkeiten statt Fallback
        available_slots = self._get_available_slots_per_weekday(participants)

        candidates = []
        today = date.today()

        for offset in range(14):
            dt = today + timedelta(days=offset)
            weekday = dt.weekday()
            if weekday >= 5:  # Skip Wochenende
                continue

            # Nur Zeiten berücksichtigen, wo ALLE verfügbar sind
            available_hours = available_slots.get(weekday, [])
            if not available_hours:
                continue

            for hour in available_hours:
                time = f"{hour:02d}:00"
                score = self._get_availability_score(participants, dt, time)
                candidates.append((dt, time, score))

        top5 = sorted(candidates, key=lambda x: x[2], reverse=True)[:5]

        # Speichere die Top-5 für die spätere Auswahl in _process_selection
        self.state.suggested_meetings = list(top5)

        response = f"📅 **Ausschuss: {self.state.selected_ausschuss.title()}**\n\nTop 5 Vorschläge:\n\n"
        for i, (dt, time, score) in enumerate(top5, 1):
            wochentag = ["Mo", "Di", "Mi", "Do", "Fr"][dt.weekday()]
            response += f"{i}. {wochentag} {dt.strftime('%d.%m.%Y')} **{time}** ({score}% OK)\n"

        response += (
            "\n💡 **Optionen:**"
            "\n- Geben Sie **1-5** ein (Top-Vorschlag)"
            "\n- Oder **Uhrzeit** (z.B. 16:00)"
            "\n- Oder **Datum** (z.B. 25.06.2026)"
        )
        self._add_response(response)
        return response

    def _parse_user_selection(self, input_str: str) -> tuple[date, str, int] | None:
        """Parse user input and return (date, time, score) oder None.

        Akzeptierte Formate:
        - "1".."5"            → Top-X Vorschlag aus suggested_meetings
        - "16:00"             → erster Vorschlag um diese Uhrzeit
        - "25.06.2026" / "25.06." → erster Vorschlag an diesem Tag (beste Stunde)
        - "25.06.2026 16:00"  → exakter Treffer Datum + Zeit
        """
        if not self.state.suggested_meetings:
            return None

        raw = input_str.strip()
        suggestions = self.state.suggested_meetings

        # 1) Reiner Index "1".."5"
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(suggestions):
                return suggestions[idx - 1]
            return None

        # 2) Datum + Zeit ("25.06.2026 16:00" oder "25.06. 16:00")
        parts = raw.split()
        if len(parts) == 2:
            parsed_date = self._parse_date_token(parts[0])
            parsed_time = self._parse_time_token(parts[1])
            if parsed_date and parsed_time:
                for dt, time, score in suggestions:
                    if dt == parsed_date and time == parsed_time:
                        return (dt, time, score)
                return None

        # 3) Nur Uhrzeit ("16:00")
        parsed_time = self._parse_time_token(raw)
        if parsed_time:
            for dt, time, score in suggestions:
                if time == parsed_time:
                    return (dt, time, score)
            return None

        # 4) Nur Datum ("25.06.2026" oder "25.06.")
        parsed_date = self._parse_date_token(raw)
        if parsed_date:
            # Bester (erster) Vorschlag an diesem Tag — Liste ist nach Score sortiert
            for dt, time, score in suggestions:
                if dt == parsed_date:
                    return (dt, time, score)
            return None

        return None

    def _parse_time_token(self, token: str) -> str | None:
        """Parse 'HH:MM' und normalisiere auf 'HH:MM'. None bei Fehler."""
        token = token.strip()
        if ":" not in token:
            return None
        try:
            parsed = datetime.strptime(token, "%H:%M")
            return parsed.strftime("%H:%M")
        except ValueError:
            return None

    def _parse_date_token(self, token: str) -> date | None:
        """Parse '25.06.2026' oder '25.06.' (aktuelles Jahr). None bei Fehler."""
        token = token.strip()
        if "." not in token:
            return None
        # Volles Datum mit Jahr
        try:
            return datetime.strptime(token, "%d.%m.%Y").date()
        except ValueError:
            pass
        # Datum ohne Jahr ("25.06." oder "25.06") → aktuelles Jahr annehmen
        token_no_trailing = token.rstrip(".")
        try:
            parsed = datetime.strptime(token_no_trailing, "%d.%m")
            return parsed.replace(year=date.today().year).date()
        except ValueError:
            return None

    def _process_selection(self, msg: str) -> str:
        """Verarbeite Haupttermin-Auswahl (Index, Uhrzeit, Datum oder Datum+Zeit)."""
        if not self.state.suggested_meetings:
            response = "⚠️ Keine Vorschläge vorhanden. Bitte starten Sie die Planung erneut."
            self._add_response(response)
            return response

        selection = self._parse_user_selection(msg)
        if selection is None:
            response = (
                "⚠️ Format: **1-5** oder **Uhrzeit** (z.B. 16:00) oder "
                "**Datum** (z.B. 25.06.2026)"
            )
            self._add_response(response)
            return response

        selected_date, selected_time, selected_score = selection
        self.state.main_meeting_selected = True
        self.state.main_meeting_date = selected_date
        self.state.main_meeting_time = selected_time

        wochentag = ["Mo", "Di", "Mi", "Do", "Fr"][selected_date.weekday()]
        termin_text = f"{wochentag} {selected_date.strftime('%d.%m.%Y')} {selected_time} ({selected_score}% OK)"
        if self.state.meeting_type == MeetingType.STR:
            response = f"✅ **Stadtratsitzung** Termin bestätigt!\n\n📅 {termin_text}\n\n📋 **Nächster Schritt:** Welche Ausschüsse sollen 1-2 Wochen vorher tagen?\n*(z.B. 'Infrastruktur, Bildung' oder 'alle')*"
        elif self.state.meeting_type == MeetingType.GR:
            response = f"✅ **Gemeinderatsitzung** Termin bestätigt!\n\n📅 {termin_text}\n\n📋 **Nächster Schritt:** Welche Ausschüsse sollen 1-2 Wochen vorher tagen?\n*(z.B. 'Infrastruktur, Bildung' oder 'alle')*"
        else:
            # OB-Flow: Ausschuss-Termin ist final → direkt persistieren.
            if self.save_planned_meetings():
                response = f"✅ **Ausschuss '{self.state.selected_ausschuss.title()}' Termin bestätigt!**\n\n📅 {termin_text}\n\n📋 Termin gespeichert. Einladungen können versendet werden."
            else:
                response = f"✅ **Ausschuss '{self.state.selected_ausschuss.title()}' Termin bestätigt!**\n\n📅 {termin_text}\n\n⚠️ Termin konnte nicht gespeichert werden."

        self._add_response(response)
        return response

    def _ask_ausschuesse_for_main_meeting(self, msg: str) -> str:
        """Frage nach Ausschüssen für STR/GR Vorbereitung + Persistierung."""
        # Erkenne Ausschüsse aus Input
        if msg == "alle":
            if not self.db:
                ausschuesse = []
            else:
                ausschuesse = self.db.query(Ausschuss).filter(
                    Ausschuss.typ == AusschussTyp.AUSSCHUSS
                ).all()
            self.state.selected_ausschuesse = [a.name for a in ausschuesse]
        else:
            names = [n.strip() for n in msg.split(",")]
            self.state.selected_ausschuesse = names

        response = f"📅 **Ausschuss-Termine vor Hauptsitzung (1-2 Wochen vorher):**\n\n"

        for ausschuss_name in self.state.selected_ausschuesse[:3]:
            self.state.selected_ausschuss = ausschuss_name
            participants = self._get_participants(MeetingType.AUSSCHUSS)

            if not participants:
                response += f"⚠️ **{ausschuss_name}:** Keine Mitglieder gefunden\n\n"
                continue

            candidates = []
            today = date.today()

            for offset in range(14):
                dt = today + timedelta(days=offset)
                if dt.weekday() >= 4:
                    continue

                for time in self.MEETING_SLOTS:
                    score = self._get_availability_score(participants, dt, time)
                    candidates.append((dt, time, score))

            top1 = sorted(candidates, key=lambda x: x[2], reverse=True)[:1]
            if top1:
                dt, time, score = top1[0]
                wochentag = ["Mo", "Di", "Mi", "Do", "Fr"][dt.weekday()]
                response += f"✓ **{ausschuss_name}:** {wochentag} {dt.strftime('%d.%m.')} {time} ({score}% OK)\n"
                # Speichere Ausschuss-Termin
                self.state.ausschuss_meetings[ausschuss_name] = (dt, time, score)

        # Speichere alle Termine in DB
        if self.save_planned_meetings():
            response += "\n✅ **Planung abgeschlossen!** Alle Termine wurden gespeichert."
        else:
            response += "\n⚠️ **Planung erstellt, aber Speicherung fehlgeschlagen.**"

        self._add_response(response)
        return response

    def _add_response(self, response: str) -> None:
        """Füge Bot-Response zu History."""
        self.state.messages.append(Message(MessageRole.ASSISTANT, response))

    def save_planned_meetings(self) -> bool:
        """Speichere geplante Sitzungen in DB."""
        if not self.db or not self.state.main_meeting_date:
            return False

        try:
            # Hauptsitzung speichern. Bei einem Ausschuss-Termin (OB-Flow)
            # verknüpfen wir die Sitzung mit dem ausgewählten Ausschuss.
            main_ausschuss_id = None
            if self.state.meeting_type == MeetingType.AUSSCHUSS and self.state.selected_ausschuss:
                ausschuss = self.db.query(Ausschuss).filter(
                    Ausschuss.name.ilike(f"%{self.state.selected_ausschuss}%")
                ).first()
                if ausschuss:
                    main_ausschuss_id = ausschuss.id

            main_meeting = PlannedMeeting(
                meeting_type=self.state.meeting_type.value.upper(),
                ausschuss_id=main_ausschuss_id,
                termin_datum=self.state.main_meeting_date,
                termin_zeit=self.state.main_meeting_time,
                verfuegbarkeit_score=100,
            )
            self.db.add(main_meeting)

            # Ausschuss-Sitzungen speichern
            for ausschuss_name, (dt, time, score) in self.state.ausschuss_meetings.items():
                ausschuss = self.db.query(Ausschuss).filter(
                    Ausschuss.name.ilike(f"%{ausschuss_name}%")
                ).first()

                if ausschuss:
                    meeting = PlannedMeeting(
                        meeting_type="AUSSCHUSS",
                        ausschuss_id=ausschuss.id,
                        termin_datum=dt,
                        termin_zeit=time,
                        verfuegbarkeit_score=score,
                    )
                    self.db.add(meeting)

            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            logger.exception("Fehler beim Speichern geplanter Meetings")
            return False

    def get_conversation_history(self) -> list[dict]:
        """Gib Chat-History als JSON."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.state.messages
        ]
