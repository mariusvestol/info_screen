import "./styles.css";

type Shift = {
  date: string;
  start: string;
  end: string;
  title: string;
  raw?: string;
  sourceCell?: string;
};

type BusDeparture = {
  line: string;
  lineName?: string | null;
  destination: string;
  expectedTime: string;
  waitMinutes: number | null;
};

type WeatherPoint = {
  time: string;
  hour: string;
  temperature: number;
  symbolCode: string | null;
  icon: string;
  label: string;
};

type WeatherSnapshot = {
  updatedAt: string;
  temperature: number;
  windSpeed: number;
  symbolCode: string | null;
  icon: string;
  label: string;
  forecast: WeatherPoint[];
};

type CalendarEvent = {
  id: string;
  calendarId: string;
  title: string;
  date: string;
  start: string;
  end: string | null;
  allDay: boolean;
};

type TodoTask = {
  id: string;
  content: string;
  dueDate: string | null;
  dueTime: string | null;
  priority: number;
  url: string | null;
};

type ShiftStatus = {
  ok: boolean;
  status: "ok" | "syncing" | "stale" | "error" | string;
  message: string;
  lastAttemptAt: string | null;
  lastSuccessAt: string | null;
  lastErrorAt: string | null;
  lastError: string | null;
  minutesSinceSuccess: number | null;
  staleMinutes: number;
};

type TrainingTopSet = {
  exercise: string;
  weight: number;
  reps: number;
  volume: number;
};

type TrainingWorkout = {
  id: string;
  name: string;
  startedAt: string | null;
  endedAt: string | null;
  durationMinutes: number | null;
  totalVolume: number;
  exerciseCount: number;
  setCount: number;
  topSet: TrainingTopSet | null;
};

type TrainingExercise = {
  name: string;
  lastWorkoutAt: string | null;
  lastWeight: number;
  lastReps: number;
  bestWeight: number;
  bestVolume: number;
  totalSets: number;
  totalReps: number;
  totalVolume: number;
};

type TrainingWeekPoint = {
  weekStart: string;
  label: string;
  sessions: number;
  volume: number;
  sets: number;
  current: boolean;
};

type TrainingSummary = {
  status: string;
  userId: string | null;
  workoutCount: number;
  week: {
    sessions: number;
    volume: number;
    sets: number;
  };
  weeklySessions?: TrainingWeekPoint[];
  lastWorkout: TrainingWorkout | null;
  exercises: TrainingExercise[];
};

type ExamFocusTopic = {
  key: string;
  label: string;
  total: number;
  solved: number;
  remaining: number;
  percent: number;
};

type ExamTask = {
  id: string;
  title: string;
  dueDate: string | null;
};

type ExamSummary = {
  status: string;
  subject: {
    key: string;
    label: string;
    title: string;
    dataPath: string;
  };
  userId: string;
  userEmail: string;
  tasksRemaining: number;
  progress: {
    total: number;
    solved: number;
    remaining: number;
    percent: number;
    practiceMore: number;
  };
  focusTopics: ExamFocusTopic[];
  nextTasks: ExamTask[];
};

type Snapshot = {
  updatedAt: string;
  shiftSyncAt: string | null;
  shiftStatus?: ShiftStatus;
  person: string;
  busError: string | null;
  buses: BusDeparture[];
  weatherError: string | null;
  weather: WeatherSnapshot | null;
  calendarUpdatedAt: string | null;
  calendarErrors: string[];
  calendarEvents: CalendarEvent[];
  todoUpdatedAt: string | null;
  todoError: string | null;
  todos: TodoTask[];
  trainingUpdatedAt: string | null;
  trainingError: string | null;
  training: TrainingSummary | null;
  examUpdatedAt: string | null;
  examError: string | null;
  exam: ExamSummary | null;
  shifts: Shift[];
};

type DisplayEvent = {
  id: string;
  date: string;
  start: string;
  end: string | null;
  title: string;
  subtitle: string;
  allDay: boolean;
  kind: "shift" | "calendar";
};

type ViewModel = {
  now: Date;
  snapshot: Snapshot | null;
};

const backgrounds = [
  "/backgrounds/Mojave-nord-light.png",
  "/backgrounds/WhiteSur-nord-light.png",
];
const SHOW_EXAM_FRAME = false;

const state: ViewModel = {
  now: new Date(),
  snapshot: null,
};

const appRoot = document.querySelector<HTMLDivElement>("#app");

if (!appRoot) {
  throw new Error("Missing #app root");
}

const app = appRoot;

function isoDate(date: Date): string {
  return date.toLocaleDateString("sv-SE", { timeZone: "Europe/Oslo" });
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function sameDate(a: string, b: Date): boolean {
  return a === isoDate(b);
}

function formatLongDate(date: Date): string {
  return new Intl.DateTimeFormat("no-NO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "Europe/Oslo",
  }).format(date);
}

function formatClock(date: Date): string {
  return new Intl.DateTimeFormat("no-NO", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Oslo",
  }).format(date);
}

function formatShortDateTime(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("no-NO", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Oslo",
  }).format(date);
}

function formatKg(value: number): string {
  return `${new Intl.NumberFormat("no-NO", {
    maximumFractionDigits: 1,
  }).format(value)} kg`;
}

function greeting(date: Date): string {
  const hour = Number(
    new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      hour12: false,
      timeZone: "Europe/Oslo",
    }).format(date),
  );

  if (hour < 12) return "God morgen";
  if (hour < 18) return "God ettermiddag";
  return "God kveld";
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

function sortShifts(shifts: Shift[]): Shift[] {
  return [...shifts].sort((a, b) => {
    const left = `${a.date}T${a.start}`;
    const right = `${b.date}T${b.start}`;
    return left.localeCompare(right);
  });
}

function eventSortKey(event: DisplayEvent): string {
  const start = event.allDay ? "00:00" : event.start;
  return `${event.date} ${start} ${event.title}`;
}

function sortEvents(events: DisplayEvent[]): DisplayEvent[] {
  return [...events].sort((a, b) => eventSortKey(a).localeCompare(eventSortKey(b)));
}

function duplicatesShift(event: CalendarEvent, shifts: Shift[]): boolean {
  const title = event.title.toLowerCase();
  return (
    title.includes("aneo") &&
    shifts.some(
      (shift) =>
        shift.date === event.date &&
        shift.start === event.start &&
        shift.end === event.end,
    )
  );
}

function toDisplayEvents(snapshot: Snapshot | null): DisplayEvent[] {
  const sourceShifts = snapshot?.shifts ?? [];
  const shifts: DisplayEvent[] = sourceShifts.map((shift) => ({
    id: `shift:${shift.date}:${shift.start}:${shift.end}:${shift.sourceCell ?? ""}`,
    date: shift.date,
    start: shift.start,
    end: shift.end,
    title: shift.title,
    subtitle: "Aneo",
    allDay: false,
    kind: "shift",
  }));

  const calendarEvents: DisplayEvent[] = (snapshot?.calendarEvents ?? [])
    .filter((event) => !duplicatesShift(event, sourceShifts))
    .map((event) => ({
      id: `calendar:${event.id}`,
      date: event.date,
      start: event.start,
      end: event.end,
      title: event.title,
      subtitle: "Kalender",
      allDay: event.allDay,
      kind: "calendar",
    }));

  return sortEvents([...shifts, ...calendarEvents]);
}

function nextShift(shifts: Shift[], now: Date): Shift | null {
  const nowKey = new Intl.DateTimeFormat("sv-SE", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Oslo",
  }).format(now);

  return (
    sortShifts(shifts).find((shift) => {
      const shiftKey = `${shift.date} ${shift.end}`;
      return shiftKey >= nowKey;
    }) ?? null
  );
}

function renderEventRow(event: DisplayEvent, compact = false): string {
  const date = new Date(`${event.date}T12:00:00`);
  const day = new Intl.DateTimeFormat("no-NO", {
    weekday: compact ? "short" : "long",
    day: "numeric",
    month: "short",
    timeZone: "Europe/Oslo",
  }).format(date);

  return `
    <li class="event-row ${event.kind}">
      <div class="event-time">${event.start}<span>${event.end ?? ""}</span></div>
      <div class="event-main">
        <div class="event-title">${escapeHtml(event.title)}</div>
        <div class="event-date">${compact ? day : event.subtitle}</div>
      </div>
    </li>
  `;
}

function renderDaySection(title: string, events: DisplayEvent[]): string {
  const visible = events.slice(0, 3);
  const hiddenCount = Math.max(0, events.length - visible.length);
  const rows = visible.length
    ? [
        visible.map((event) => renderEventRow(event)).join(""),
        hiddenCount ? `<li class="more-row">+${hiddenCount} til</li>` : "",
      ].join("")
    : `<li class="empty-row">Ingen hendelser</li>`;

  return `
    <section class="panel day-panel">
      <div class="panel-heading">${title}</div>
      <ul class="event-list">${rows}</ul>
    </section>
  `;
}

function renderBusPanel(snapshot: Snapshot | null): string {
  const buses = snapshot?.buses.slice(0, 3) ?? [];
  const rows = buses.length
    ? buses
        .map((bus) => {
          const wait = bus.waitMinutes === null ? "N/A" : `${bus.waitMinutes} min`;
          return `
            <li class="bus-row">
              <div class="route-pill">${bus.line}</div>
              <div class="bus-destination">${escapeHtml(bus.destination)}</div>
              <div class="bus-wait">${wait}</div>
            </li>
          `;
        })
        .join("")
    : `<li class="empty-row">${snapshot?.busError ? "Ingen bussdata" : "Laster bussdata"}</li>`;

  return `
    <section class="panel bus-panel">
      <div class="panel-heading">Buss</div>
      <ul class="bus-list">${rows}</ul>
    </section>
  `;
}

function shortTime(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat("no-NO", {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Oslo",
  }).format(date);
}

function renderShiftStatusBanner(snapshot: Snapshot | null): string {
  const status = snapshot?.shiftStatus;
  if (!status || status.ok) {
    return "";
  }

  const lastOk = shortTime(status.lastSuccessAt);
  const detail = lastOk ? `Sist OK ${lastOk}` : "Ingen vellykket Excel-sync";
  const error = status.lastError ? `<span>${escapeHtml(status.lastError)}</span>` : "";

  return `
    <section class="status-banner ${status.status === "stale" ? "stale" : "error"}">
      <div>
        <strong>Excel-varsel</strong>
        <p>${escapeHtml(status.message)}</p>
      </div>
      <div class="status-detail">
        <small>${escapeHtml(detail)}</small>
        ${error}
      </div>
    </section>
  `;
}

function formatTodoDue(task: TodoTask, now: Date): string {
  if (!task.dueDate) {
    return "TBD";
  }

  const suffix = task.dueTime ? ` ${task.dueTime}` : "";
  if (sameDate(task.dueDate, now)) return `I dag${suffix}`;
  if (sameDate(task.dueDate, addDays(now, 1))) return `I morgen${suffix}`;

  const date = new Date(`${task.dueDate}T12:00:00`);
  const label = new Intl.DateTimeFormat("no-NO", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "Europe/Oslo",
  }).format(date);

  return `${label}${suffix}`;
}

function renderTodoPanel(snapshot: Snapshot | null, now: Date): string {
  const allTasks = snapshot?.todos ?? [];
  const tasks = allTasks.slice(0, 4);
  const hiddenCount = Math.max(0, allTasks.length - tasks.length);
  const rows = tasks.length
    ? tasks
        .map(
          (task) => `
            <li class="todo-row priority-${task.priority}">
              <div class="todo-due">${formatTodoDue(task, now)}</div>
              <div class="todo-content">${escapeHtml(task.content)}</div>
            </li>
          `,
        )
        .join("") + (hiddenCount ? `<li class="more-row">+${hiddenCount} til</li>` : "")
    : `<li class="empty-row">${snapshot?.todoError ? "Ingen Todoist-data" : "Ingen oppgaver"}</li>`;

  return `
    <section class="panel todo-panel">
      <div class="panel-heading">Tasks</div>
      <ul class="todo-list">${rows}</ul>
    </section>
  `;
}

function renderTrainingPanel(snapshot: Snapshot | null): string {
  const training = snapshot?.training;
  const workout = training?.lastWorkout;
  if (!training || !workout) {
    return `
      <section class="panel training-panel">
        <div class="panel-heading">Trening</div>
        <div class="empty-row">${snapshot?.trainingError ? "Ingen treningsdata" : "Laster trening"}</div>
      </section>
    `;
  }

  const topSet = workout.topSet;
  const weeklySessions = training.weeklySessions ?? [];
  const maxSessions = Math.max(1, ...weeklySessions.map((point) => point.sessions));
  const midSessions = Math.ceil(maxSessions / 2);
  const graphRows = weeklySessions
    .map((point) => {
      const barHeight = point.sessions > 0 ? Math.max(12, Math.round((point.sessions / maxSessions) * 100)) : 4;
      const barValue = point.sessions > 0 ? String(point.sessions) : "";
      return `
        <li class="training-bar ${point.current ? "current" : ""}" style="--bar-height: ${barHeight}%">
          <span class="training-bar-value">${barValue}</span>
          <span class="training-bar-track"><span class="training-bar-fill"></span></span>
          <span class="training-bar-label">${escapeHtml(point.label)}</span>
        </li>
      `;
    })
    .join("");

  return `
    <section class="panel training-panel">
      <div class="panel-heading">Trening</div>
      <div class="training-grid">
        <div class="training-primary">
          <span>Siste økt</span>
          <strong>${escapeHtml(workout.name)}</strong>
          <small>${formatShortDateTime(workout.startedAt)}</small>
        </div>
        <div class="training-stat">
          <span>Denne uka</span>
          <strong>${training.week.sessions}</strong>
          <small>${formatKg(training.week.volume)}</small>
        </div>
        <div class="training-stat">
          <span>Sett</span>
          <strong>${workout.setCount}</strong>
          <small>${workout.exerciseCount} øvelser</small>
        </div>
      </div>
      ${
        graphRows
          ? `
            <div class="training-chart">
              <div class="training-y-axis">
                <span>${maxSessions}</span>
                <span>${maxSessions > 1 ? midSessions : ""}</span>
                <span>0</span>
              </div>
              <ul class="training-bars">${graphRows}</ul>
            </div>
          `
          : ""
      }
      ${
        topSet
          ? `
            <div class="training-highlight">
              <span>${escapeHtml(topSet.exercise)}</span>
              <strong>${formatKg(topSet.weight)} x ${topSet.reps}</strong>
            </div>
          `
          : ""
      }
    </section>
  `;
}

function renderExamPanel(snapshot: Snapshot | null): string {
  const exam = snapshot?.exam;
  const title = exam?.subject?.title ?? "Eksamen";
  if (!exam) {
    return `
      <section class="panel exam-panel">
        <div class="panel-heading">${title}</div>
        <div class="empty-row">${snapshot?.examError ? "Ingen eksamensdata" : "Laster eksamen"}</div>
      </section>
    `;
  }

  const progress = exam.progress;
  const progressWidth = Math.max(4, Math.min(100, progress.percent));
  const focus = exam.focusTopics
    .slice(0, 2)
    .map((topic) => `${escapeHtml(topic.label)} ${topic.percent}%`)
    .join(" · ");

  return `
    <section class="panel exam-panel">
      <div class="exam-topline">
        <div>
          <div class="panel-heading">${escapeHtml(title)}</div>
          <p>${progress.solved}/${progress.total} spørsmål</p>
        </div>
        <strong>${progress.percent}%</strong>
      </div>
      <div class="exam-meter" style="--exam-progress: ${progressWidth}%">
        <span></span>
      </div>
      <div class="exam-grid">
        <div>
          <span>Tasks</span>
          <strong>${exam.tasksRemaining}</strong>
          <small>gjenstående</small>
        </div>
        <div>
          <span>Igjen</span>
          <strong>${progress.remaining}</strong>
          <small>spørsmål</small>
        </div>
        <div>
          <span>Øv mer</span>
          <strong>${progress.practiceMore}</strong>
          <small>markert</small>
        </div>
      </div>
      <div class="exam-focus">
        <span>Fokus</span>
        <strong>${focus || "Ingen svake tema"}</strong>
      </div>
    </section>
  `;
}

function renderWeatherHero(snapshot: Snapshot | null): string {
  const weather = snapshot?.weather;
  if (!weather) {
    return `
      <div class="weather-hero">
        <p class="eyebrow">Vær</p>
        <div class="weather-empty">Ingen data</div>
      </div>
    `;
  }

  const forecast = weather.forecast
    .slice(0, 3)
    .map(
      (point) => `
        <li>
          <span>${point.hour}</span>
          <img src="${point.icon}" alt="${point.label}" />
          <strong>${point.temperature}°</strong>
        </li>
      `,
    )
    .join("");

  return `
    <div class="weather-hero">
      <p class="eyebrow">Vær</p>
      <div class="weather-now">
        <img src="${weather.icon}" alt="${weather.label}" />
        <div>
          <strong>${weather.temperature}°</strong>
          <span>${weather.label}</span>
        </div>
      </div>
      <ul class="weather-forecast">${forecast}</ul>
    </div>
  `;
}

function render(snapshot: Snapshot | null): void {
  const now = state.now;
  const shifts = sortShifts(snapshot?.shifts ?? []);
  const events = toDisplayEvents(snapshot);
  const today = now;
  const tomorrow = addDays(now, 1);
  const todayEvents = events.filter((event) => sameDate(event.date, today));
  const tomorrowEvents = events.filter((event) => sameDate(event.date, tomorrow));
  const upcoming = events
    .filter((event) => event.date >= isoDate(addDays(today, 2)))
    .slice(0, 4);
  const next = nextShift(shifts, now);

  app.innerHTML = `
    <main class="screen">
      <section class="topline">
        <div>
          <p class="eyebrow">${formatLongDate(now)}</p>
          <h1>${greeting(now)}</h1>
        </div>
        <div class="clock">${formatClock(now)}</div>
      </section>

      ${renderShiftStatusBanner(snapshot)}

      <section class="hero-panel">
        <div>
          <p class="eyebrow">Neste vakt</p>
          <h2>${next ? `${next.start}-${next.end}` : "Ingen kommende vakt"}</h2>
          <p>${next ? formatLongDate(new Date(`${next.date}T12:00:00`)) : ""}</p>
        </div>
        ${renderWeatherHero(snapshot)}
      </section>

      <div class="stack">
        ${renderBusPanel(snapshot)}
        ${renderDaySection("I dag", todayEvents)}
        ${renderDaySection("I morgen", tomorrowEvents)}
        ${renderTodoPanel(snapshot, now)}

        <section class="panel upcoming-panel">
          <div class="panel-heading">Kommende</div>
          <ul class="event-list upcoming">
            ${
              upcoming.length
                ? upcoming.map((event) => renderEventRow(event, true)).join("")
                : `<li class="empty-row">Ingen hendelser</li>`
            }
          </ul>
        </section>

        ${renderTrainingPanel(snapshot)}
        ${SHOW_EXAM_FRAME ? renderExamPanel(snapshot) : ""}
      </div>

      <footer>
        <span>${snapshot?.person ?? "Marius V"}</span>
        <span>${snapshot?.shiftSyncAt ? `Sync ${snapshot.shiftSyncAt.slice(11, 16)}` : "Ingen sync"}</span>
      </footer>
    </main>
  `;
}

async function loadSnapshot(): Promise<void> {
  try {
    const response = await fetch(`/data/snapshot.json?t=${Date.now()}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`snapshot ${response.status}`);
    }

    state.snapshot = (await response.json()) as Snapshot;
  } catch (error) {
    console.error("Could not load snapshot", error);
  }

  render(state.snapshot);
}

function startClock(): void {
  window.setInterval(() => {
    state.now = new Date();
    render(state.snapshot);
  }, 1000);
}

function startBackgroundCycle(): void {
  let index = 0;
  document.documentElement.style.setProperty("--screen-bg", `url("${backgrounds[index]}")`);

  for (const src of backgrounds) {
    const img = new Image();
    img.src = src;
  }

  window.setInterval(() => {
    index = (index + 1) % backgrounds.length;
    document.documentElement.style.setProperty("--screen-bg", `url("${backgrounds[index]}")`);
  }, 10 * 60 * 1000);
}

startBackgroundCycle();
startClock();
void loadSnapshot();
window.setInterval(loadSnapshot, 60 * 1000);
