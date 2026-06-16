import { spawnSync } from "node:child_process";
import { createSign } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import vm from "node:vm";

const projectRoot = resolve(dirname(new URL(import.meta.url).pathname), "..");
const infoScreenRoot = resolve(projectRoot, "..");
loadEnvFile(resolve(infoScreenRoot, ".env"));

const outPath = resolve(projectRoot, "public/data/snapshot.json");
const dbPath = process.env.SHIFT_PLAN_DB ?? "/home/marves/Desktop/info_screen/shift_plan.db";
const trainingDbPath = process.env.TRAINING_DB ?? "/home/marves/Desktop/info_screen/training.db";
const examDbPath = process.env.EXAM_DB ?? "/home/marves/Desktop/database.db";
const websiteRoot = process.env.WEBSITE_ROOT ?? "/home/marves/Desktop/website";
const examAnswerUtilsPath = process.env.EXAM_ANSWER_UTILS ?? resolve(websiteRoot, "assets/js/exam-answer-utils.js");
const examSubjectRegistryPath =
  process.env.EXAM_SUBJECT_REGISTRY ?? resolve(websiteRoot, "assets/js/exam-subject-registry.js");
const examSubjectKey = String(process.env.EXAM_SUBJECT ?? "os").trim().toLowerCase();
const examUserEmail = process.env.EXAM_USER_EMAIL ?? "marius.vestol@gmail.com";
const shiftStaleMinutes = Number(process.env.SHIFT_STALE_MINUTES ?? 45);
const googleKeyPath = process.env.GOOGLE_CALENDAR_KEY ?? "/home/marves/Desktop/info_screen/key.json";
const legacyTodoFramePath = "/home/marves/Desktop/info_screen/TodoFrame.py";
const todoistToken = process.env.TODOIST_API_TOKEN ?? readLegacyTodoistToken();
const googleCalendarIds = [
  "marius.vestoel@abakus.no",
  "marves@samfundet.no",
  "marius.vestol@gmail.com",
];
const googleScope = "https://www.googleapis.com/auth/calendar.readonly";
const todoistUrl = "https://api.todoist.com/api/v1/tasks";
const weatherUrl = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=63.4305&lon=10.3951";
const weatherHeaders = {
  "User-Agent": "marves-info-screen/0.1 contact: local-rpi",
};
const enturUrl = "https://api.entur.io/journey-planner/v3/graphql";
const enturHeaders = {
  "Content-Type": "application/json",
  "ET-Client-Name": "marves-info-screen-web",
};
const enturQuery = `
{
  quay(id: "NSR:Quay:74792") {
    estimatedCalls(timeRange: 7200, numberOfDepartures: 5) {
      expectedArrivalTime
      destinationDisplay {
        frontText
      }
      serviceJourney {
        line {
          publicCode
          name
        }
      }
    }
  }
}
`;

function loadEnvFile(path) {
  if (!existsSync(path)) {
    return;
  }

  for (const rawLine of readFileSync(path, "utf8").split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) {
      continue;
    }

    const [key, ...rest] = line.split("=");
    if (!key.trim() || process.env[key.trim()] !== undefined) {
      continue;
    }

    process.env[key.trim()] = rest.join("=").trim().replace(/^["']|["']$/g, "");
  }
}

function sqliteJsonFrom(databasePath, query) {
  const result = spawnSync("sqlite3", ["-readonly", "-json", databasePath, query], {
    encoding: "utf8",
  });

  if (result.status !== 0) {
    throw new Error(result.stderr.trim() || `sqlite3 exited with ${result.status}`);
  }

  return JSON.parse(result.stdout || "[]");
}

function sqliteJson(query) {
  return sqliteJsonFrom(dbPath, query);
}

function sqlString(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

function readPreviousSnapshot() {
  if (!existsSync(outPath)) {
    return null;
  }

  try {
    return JSON.parse(readFileSync(outPath, "utf8"));
  } catch {
    return null;
  }
}

const previousSnapshot = readPreviousSnapshot();
let shifts = [];
let meta = {};
let shiftReadError = null;

try {
  shifts = sqliteJson(`
    SELECT
      shift_date AS date,
      start_time AS start,
      end_time AS end,
      'Jobb (Aneo)' AS title,
      raw_value AS raw,
      source_cell AS sourceCell
    FROM shifts
    WHERE shift_date >= date('now', 'localtime', '-1 day')
    ORDER BY shift_date, start_time
  `);

  const metaRows = sqliteJson("SELECT key, value FROM sync_meta ORDER BY key");
  meta = Object.fromEntries(metaRows.map((row) => [row.key, row.value]));
} catch (error) {
  shiftReadError = error instanceof Error ? error.message : String(error);
  shifts = previousSnapshot?.shifts ?? [];
  meta = {};
}

function readLegacyTodoistToken() {
  if (!existsSync(legacyTodoFramePath)) {
    return null;
  }

  const source = readFileSync(legacyTodoFramePath, "utf8");
  const match = source.match(/self\.api_token\s*=\s*["']([^"']+)["']/);
  return match?.[1] ?? null;
}

function base64url(input) {
  return Buffer.from(input)
    .toString("base64")
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

function signJwt(serviceAccount) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const claims = {
    iss: serviceAccount.client_email,
    scope: googleScope,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  };
  const unsigned = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(claims))}`;
  const signer = createSign("RSA-SHA256");
  signer.update(unsigned);
  signer.end();
  return `${unsigned}.${signer.sign(serviceAccount.private_key, "base64url")}`;
}

async function getGoogleAccessToken() {
  const serviceAccount = JSON.parse(readFileSync(googleKeyPath, "utf8"));
  const assertion = signJwt(serviceAccount);
  const body = new URLSearchParams({
    grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
    assertion,
  });

  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!response.ok) {
    throw new Error(`Google token ${response.status} ${response.statusText}`);
  }

  const payload = await response.json();
  return payload.access_token;
}

function osloDate(value) {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Europe/Oslo",
  }).format(new Date(value));
}

function osloTime(value) {
  return new Intl.DateTimeFormat("no-NO", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Oslo",
  }).format(new Date(value));
}

function normalizeCalendarEvent(item, calendarId) {
  const startDate = item.start?.date;
  const startDateTime = item.start?.dateTime;
  const endDateTime = item.end?.dateTime;
  const isAllDay = Boolean(startDate);

  return {
    id: `${calendarId}:${item.id}`,
    calendarId,
    title: item.summary || "Uten tittel",
    date: isAllDay ? startDate : osloDate(startDateTime),
    start: isAllDay ? "Heldag" : osloTime(startDateTime),
    end: isAllDay || !endDateTime ? null : osloTime(endDateTime),
    allDay: isAllDay,
  };
}

async function fetchCalendarEvents(previousSnapshot) {
  const cachedEvents = previousSnapshot?.calendarEvents;
  const cachedAt = previousSnapshot?.calendarUpdatedAt;
  if (Array.isArray(cachedEvents) && cachedAt) {
    const ageMs = Date.now() - Date.parse(cachedAt);
    if (Number.isFinite(ageMs) && ageMs < 5 * 60 * 1000) {
      return { events: cachedEvents, updatedAt: cachedAt, errors: previousSnapshot?.calendarErrors ?? [] };
    }
  }

  const token = await getGoogleAccessToken();
  const timeMin = new Date().toISOString();
  const timeMax = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString();
  const events = [];
  const errors = [];

  for (const calendarId of googleCalendarIds) {
    const params = new URLSearchParams({
      timeMin,
      timeMax,
      singleEvents: "true",
      orderBy: "startTime",
      showDeleted: "false",
      maxResults: "40",
    });
    const url = `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events?${params}`;
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      errors.push(`${calendarId}: ${response.status} ${response.statusText}`);
      continue;
    }

    const payload = await response.json();
    for (const item of payload.items ?? []) {
      events.push(normalizeCalendarEvent(item, calendarId));
    }
  }

  events.sort((a, b) => `${a.date} ${a.start}`.localeCompare(`${b.date} ${b.start}`));
  return { events, updatedAt: new Date().toISOString(), errors };
}

function normalizeTodoistTask(task) {
  const due = task?.due ?? null;
  const hasTime = Boolean(due?.datetime);
  const dueDate = due?.date ?? (due?.datetime ? osloDate(due.datetime) : null);
  const dueTime = hasTime ? osloTime(due.datetime) : null;

  return {
    id: String(task.id ?? task.task_id ?? task.content),
    content: task.content || "Uten tittel",
    dueDate,
    dueTime,
    priority: Number(task.priority ?? 1),
    url: task.url ?? null,
  };
}

function todoSortKey(task) {
  const date = task.dueDate ?? "9999-12-31";
  const time = task.dueTime ?? "00:00";
  return `${date} ${time} ${5 - task.priority} ${task.content}`;
}

async function fetchTodoistTasks() {
  if (!todoistToken) {
    throw new Error("Missing Todoist token");
  }

  const response = await fetch(todoistUrl, {
    headers: { Authorization: `Bearer ${todoistToken}` },
  });

  if (!response.ok) {
    throw new Error(`Todoist ${response.status} ${response.statusText}`);
  }

  const payload = await response.json();
  const rawTasks = Array.isArray(payload) ? payload : payload.results ?? [];
  return rawTasks
    .map(normalizeTodoistTask)
    .sort((a, b) => todoSortKey(a).localeCompare(todoSortKey(b)))
    .slice(0, 8);
}

function iconForSymbol(symbolCode) {
  const code = String(symbolCode ?? "").toLowerCase();
  if (code.includes("thunder")) return "/weather-icons/thunderstorm.png";
  if (code.includes("snow") || code.includes("sleet")) return "/weather-icons/snowy.png";
  if (code.includes("rain") || code.includes("drizzle")) return "/weather-icons/rainy.png";
  if (code.includes("cloudy") || code.includes("fog")) return "/weather-icons/cloudy.png";
  if (code.includes("partly") || code.includes("fair")) return "/weather-icons/partly_cloudy.png";
  if (code.includes("night")) return "/weather-icons/moon.png";
  return "/weather-icons/sun.png";
}

function labelForSymbol(symbolCode) {
  const code = String(symbolCode ?? "").toLowerCase();
  if (code.includes("thunder")) return "Torden";
  if (code.includes("snow")) return "Snø";
  if (code.includes("sleet")) return "Sludd";
  if (code.includes("rain") || code.includes("drizzle")) return "Regn";
  if (code.includes("fog")) return "Tåke";
  if (code.includes("cloudy")) return "Skyet";
  if (code.includes("partly")) return "Delvis skyet";
  if (code.includes("fair")) return "Lettskyet";
  if (code.includes("clear")) return "Klart";
  return "Vær";
}

function weatherPointFromTimeseries(item) {
  const details = item?.data?.instant?.details ?? {};
  const symbolCode =
    item?.data?.next_1_hours?.summary?.symbol_code ??
    item?.data?.next_6_hours?.summary?.symbol_code ??
    null;
  return {
    time: item.time,
    hour: new Intl.DateTimeFormat("no-NO", {
      hour: "2-digit",
      timeZone: "Europe/Oslo",
    }).format(new Date(item.time)),
    temperature: Math.round(Number(details.air_temperature)),
    symbolCode,
    icon: iconForSymbol(symbolCode),
    label: labelForSymbol(symbolCode),
  };
}

async function fetchWeather(previousSnapshot) {
  const cachedWeather = previousSnapshot?.weather;
  if (cachedWeather?.updatedAt) {
    const ageMs = Date.now() - Date.parse(cachedWeather.updatedAt);
    if (Number.isFinite(ageMs) && ageMs < 20 * 60 * 1000) {
      return cachedWeather;
    }
  }

  const response = await fetch(weatherUrl, { headers: weatherHeaders });
  if (!response.ok) {
    throw new Error(`met.no ${response.status} ${response.statusText}`);
  }

  const payload = await response.json();
  const timeseries = payload?.properties?.timeseries ?? [];
  const current = timeseries[0];
  if (!current) {
    throw new Error("met.no returned no timeseries");
  }

  const details = current.data.instant.details ?? {};
  const symbolCode =
    current.data.next_1_hours?.summary?.symbol_code ??
    current.data.next_6_hours?.summary?.symbol_code ??
    null;

  return {
    updatedAt: new Date().toISOString(),
    temperature: Math.round(Number(details.air_temperature)),
    windSpeed: Number(details.wind_speed ?? 0),
    symbolCode,
    icon: iconForSymbol(symbolCode),
    label: labelForSymbol(symbolCode),
    forecast: timeseries.slice(1, 5).map(weatherPointFromTimeseries),
  };
}

async function fetchBusDepartures() {
  const response = await fetch(enturUrl, {
    method: "POST",
    headers: enturHeaders,
    body: JSON.stringify({ query: enturQuery }),
  });

  if (!response.ok) {
    throw new Error(`Entur ${response.status} ${response.statusText}`);
  }

  const payload = await response.json();
  const calls = payload?.data?.quay?.estimatedCalls ?? [];
  const now = Date.now();

  return calls.map((call) => {
    const expectedTime = call.expectedArrivalTime;
    const arrivalMs = Date.parse(expectedTime);
    const waitMinutes = Number.isFinite(arrivalMs)
      ? Math.max(0, Math.round((arrivalMs - now) / 60000))
      : null;

    return {
      line: call.serviceJourney?.line?.publicCode ?? call.serviceJourney?.line?.name ?? "?",
      lineName: call.serviceJourney?.line?.name ?? null,
      destination: call.destinationDisplay?.frontText ?? "Ukjent",
      expectedTime,
      waitMinutes,
    };
  });
}

function cleanMeta(value) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function minutesSinceIso(value) {
  if (!value) {
    return null;
  }

  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) {
    return null;
  }

  return Math.max(0, Math.floor((Date.now() - timestamp) / 60000));
}

function startOfLocalWeek(date) {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  const day = start.getDay() || 7;
  start.setDate(start.getDate() - day + 1);
  return start;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function isoDateOnly(date) {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Europe/Oslo",
  }).format(date);
}

function isoWeekNumber(date) {
  const target = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNumber = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - dayNumber);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  return Math.ceil(((target.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

function workoutStartedMs(workout) {
  const timestamp = Date.parse(workout.startedAt ?? workout.createdAt ?? "");
  return Number.isFinite(timestamp) ? timestamp : null;
}

function buildWeeklyTrainingSeries(workouts, numberOfWeeks = 8) {
  const currentWeekStart = startOfLocalWeek(new Date());

  return Array.from({ length: numberOfWeeks }, (_, index) => {
    const weekStart = addDays(currentWeekStart, (index - numberOfWeeks + 1) * 7);
    const nextWeekStart = addDays(weekStart, 7);
    const weekStartMs = weekStart.getTime();
    const nextWeekStartMs = nextWeekStart.getTime();
    const weekWorkouts = workouts.filter((workout) => {
      const started = workoutStartedMs(workout);
      return started !== null && started >= weekStartMs && started < nextWeekStartMs;
    });

    return {
      weekStart: isoDateOnly(weekStart),
      label: `U${isoWeekNumber(weekStart)}`,
      sessions: weekWorkouts.length,
      volume: roundNumber(weekWorkouts.reduce((sum, workout) => sum + Number(workout.totalVolume ?? 0), 0)),
      sets: weekWorkouts.reduce((sum, workout) => sum + Number(workout.setCount ?? 0), 0),
      current: index === numberOfWeeks - 1,
    };
  });
}

function roundNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.round(number * 10) / 10;
}

function buildTrainingSummary(previousSnapshot) {
  if (!existsSync(trainingDbPath)) {
    return {
      training: previousSnapshot?.training ?? null,
      updatedAt: previousSnapshot?.trainingUpdatedAt ?? null,
      error: "training.db finnes ikke ennå",
    };
  }

  const workouts = sqliteJsonFrom(
    trainingDbPath,
    `
      SELECT
        id,
        name,
        started_at AS startedAt,
        ended_at AS endedAt,
        created_at AS createdAt,
        total_volume AS totalVolume,
        exercise_count AS exerciseCount,
        set_count AS setCount,
        top_set_exercise AS topSetExercise,
        top_set_weight AS topSetWeight,
        top_set_reps AS topSetReps,
        top_set_volume AS topSetVolume
      FROM training_workouts
      ORDER BY started_at DESC
      LIMIT 120
    `,
  );
  const exercises = sqliteJsonFrom(
    trainingDbPath,
    `
      SELECT
        exercise_name AS name,
        last_workout_at AS lastWorkoutAt,
        last_weight AS lastWeight,
        last_reps AS lastReps,
        best_weight AS bestWeight,
        best_volume AS bestVolume,
        total_sets AS totalSets,
        total_reps AS totalReps,
        total_volume AS totalVolume
      FROM training_exercise_stats
      ORDER BY total_volume DESC
      LIMIT 4
    `,
  );
  const metaRows = sqliteJsonFrom(trainingDbPath, "SELECT key, value FROM training_sync_meta ORDER BY key");
  const trainingMeta = Object.fromEntries(metaRows.map((row) => [row.key, row.value]));
  const lastWorkout = workouts[0] ?? null;
  const weekStart = startOfLocalWeek(new Date());
  const weekWorkouts = workouts.filter((workout) => {
    const started = Date.parse(workout.startedAt ?? workout.createdAt ?? "");
    return Number.isFinite(started) && started >= weekStart.getTime();
  });

  const durationMinutes =
    lastWorkout?.startedAt && lastWorkout?.endedAt
      ? Math.max(0, Math.round((Date.parse(lastWorkout.endedAt) - Date.parse(lastWorkout.startedAt)) / 60000))
      : null;

  return {
    updatedAt: cleanMeta(trainingMeta.last_success_at) ?? null,
    error: cleanMeta(trainingMeta.last_error),
    training: {
      status: cleanMeta(trainingMeta.status) ?? "unknown",
      userId: cleanMeta(trainingMeta.user_id),
      workoutCount: Number(trainingMeta.workout_count ?? workouts.length),
      week: {
        sessions: weekWorkouts.length,
        volume: roundNumber(weekWorkouts.reduce((sum, workout) => sum + Number(workout.totalVolume ?? 0), 0)),
        sets: weekWorkouts.reduce((sum, workout) => sum + Number(workout.setCount ?? 0), 0),
      },
      weeklySessions: buildWeeklyTrainingSeries(workouts),
      lastWorkout: lastWorkout
        ? {
            id: lastWorkout.id,
            name: lastWorkout.name,
            startedAt: lastWorkout.startedAt,
            endedAt: lastWorkout.endedAt,
            durationMinutes,
            totalVolume: roundNumber(lastWorkout.totalVolume),
            exerciseCount: Number(lastWorkout.exerciseCount ?? 0),
            setCount: Number(lastWorkout.setCount ?? 0),
            topSet: lastWorkout.topSetExercise
              ? {
                  exercise: lastWorkout.topSetExercise,
                  weight: roundNumber(lastWorkout.topSetWeight),
                  reps: Number(lastWorkout.topSetReps ?? 0),
                  volume: roundNumber(lastWorkout.topSetVolume),
                }
              : null,
          }
        : null,
      exercises: exercises.map((exercise) => ({
        name: exercise.name,
        lastWorkoutAt: exercise.lastWorkoutAt,
        lastWeight: roundNumber(exercise.lastWeight),
        lastReps: Number(exercise.lastReps ?? 0),
        bestWeight: roundNumber(exercise.bestWeight),
        bestVolume: roundNumber(exercise.bestVolume),
        totalSets: Number(exercise.totalSets ?? 0),
        totalReps: Number(exercise.totalReps ?? 0),
        totalVolume: roundNumber(exercise.totalVolume),
      })),
    },
  };
}

function loadExamCatalog() {
  if (!existsSync(examSubjectRegistryPath)) {
    throw new Error("Exam subject registry finnes ikke");
  }

  if (!existsSync(examAnswerUtilsPath)) {
    throw new Error("Exam answer utils finnes ikke");
  }

  const context = { window: {} };
  vm.createContext(context);
  vm.runInContext(readFileSync(examAnswerUtilsPath, "utf8"), context, {
    filename: examAnswerUtilsPath,
    timeout: 1000,
  });
  vm.runInContext(readFileSync(examSubjectRegistryPath, "utf8"), context, {
    filename: examSubjectRegistryPath,
    timeout: 1000,
  });

  const registry = context.window.ExamSubjectRegistry;
  const subject = registry?.getSubjectConfig?.(examSubjectKey);
  if (!subject) {
    const available = Object.keys(registry?.SUBJECTS ?? {}).join(", ") || "ukjent";
    throw new Error(`Ukjent eksamensfag '${examSubjectKey}'. Tilgjengelig: ${available}`);
  }

  const dataScript = String(subject.dataScript ?? "").split("?")[0];
  const dataPath = resolve(websiteRoot, "safe_exam", dataScript);
  if (!existsSync(dataPath)) {
    throw new Error(`Eksamensdata finnes ikke for ${subject.label}: ${dataPath}`);
  }

  vm.runInContext(readFileSync(dataPath, "utf8"), context, {
    filename: dataPath,
    timeout: 1000,
  });

  const items = Array.isArray(context.window[subject.itemsGlobal]) ? context.window[subject.itemsGlobal] : [];
  const topics = Array.isArray(subject.topics) ? subject.topics : [];
  if (!items.length) {
    throw new Error(`Fant ingen eksamensspørsmål for ${subject.label}`);
  }

  return {
    subject: {
      key: subject.key,
      label: subject.label,
      title: `${subject.label} Eksamen`,
      dataPath,
    },
    items,
    topics,
  };
}

function buildExamSummary(previousSnapshot) {
  if (!existsSync(examDbPath)) {
    return {
      exam: previousSnapshot?.exam ?? null,
      updatedAt: previousSnapshot?.examUpdatedAt ?? null,
      error: "database.db finnes ikke",
    };
  }

  const userRows = sqliteJsonFrom(
    examDbPath,
    `
      SELECT id, email
      FROM users
      WHERE lower(email) = lower(${sqlString(examUserEmail)})
      LIMIT 1
    `,
  );
  const user = userRows[0] ?? null;
  if (!user) {
    return {
      exam: previousSnapshot?.exam ?? null,
      updatedAt: previousSnapshot?.examUpdatedAt ?? null,
      error: `Fant ikke user ${examUserEmail}`,
    };
  }

  const { subject, items, topics } = loadExamCatalog();
  const itemIds = new Set(items.map((item) => item.id).filter(Boolean));
  const userId = user.id;
  const userIdSql = sqlString(userId);

  const progressRows = sqliteJsonFrom(
    examDbPath,
    `SELECT item_id AS itemId FROM exam_progress WHERE user_id = ${userIdSql}`,
  );
  const practiceRows = sqliteJsonFrom(
    examDbPath,
    `SELECT item_id AS itemId FROM exam_practice_more WHERE user_id = ${userIdSql}`,
  );
  const taskRows = sqliteJsonFrom(
    examDbPath,
    `
      SELECT id, title, due_date AS dueDate, created_at AS createdAt
      FROM tasks
      WHERE user_id = ${userIdSql}
      ORDER BY due_date IS NULL, due_date, created_at DESC
      LIMIT 3
    `,
  );
  const taskCountRows = sqliteJsonFrom(
    examDbPath,
    `SELECT count(*) AS count FROM tasks WHERE user_id = ${userIdSql}`,
  );

  const solvedIds = new Set(
    progressRows.map((row) => row.itemId).filter((itemId) => itemIds.has(itemId)),
  );
  const practiceIds = new Set(
    practiceRows.map((row) => row.itemId).filter((itemId) => itemIds.has(itemId)),
  );
  const total = items.length;
  const solved = solvedIds.size;
  const remaining = Math.max(0, total - solved);
  const percent = total ? Math.round((solved / total) * 100) : 0;
  const topicStats = topics
    .map((topic) => {
      const topicItems = items.filter((item) => item.topic === topic.key);
      const topicSolved = topicItems.filter((item) => solvedIds.has(item.id)).length;
      const topicTotal = topicItems.length;
      const topicRemaining = Math.max(0, topicTotal - topicSolved);
      return {
        key: topic.key,
        label: topic.label,
        total: topicTotal,
        solved: topicSolved,
        remaining: topicRemaining,
        percent: topicTotal ? Math.round((topicSolved / topicTotal) * 100) : 0,
      };
    })
    .filter((topic) => topic.total > 0);

  const focusTopics = [...topicStats]
    .filter((topic) => topic.remaining > 0)
    .sort((a, b) => a.percent - b.percent || b.remaining - a.remaining)
    .slice(0, 3);

  return {
    updatedAt: new Date().toISOString(),
    error: null,
    exam: {
      status: "ok",
      subject,
      userId,
      userEmail: user.email,
      tasksRemaining: Number(taskCountRows[0]?.count ?? taskRows.length),
      progress: {
        total,
        solved,
        remaining,
        percent,
        practiceMore: practiceIds.size,
      },
      focusTopics,
      nextTasks: taskRows.map((task) => ({
        id: task.id,
        title: task.title,
        dueDate: task.dueDate ?? null,
      })),
    },
  };
}

function buildShiftStatus() {
  const lastSuccessAt =
    cleanMeta(meta.last_success_at) ??
    cleanMeta(meta.last_sync_at) ??
    previousSnapshot?.shiftStatus?.lastSuccessAt ??
    previousSnapshot?.shiftSyncAt ??
    null;
  const lastAttemptAt = cleanMeta(meta.last_attempt_at) ?? previousSnapshot?.shiftStatus?.lastAttemptAt ?? null;
  const lastError = cleanMeta(meta.last_error) ?? null;
  const lastErrorAt = lastError ? cleanMeta(meta.last_error_at) : null;
  const metaStatus = cleanMeta(meta.status) ?? "unknown";
  const minutesSinceSuccess = minutesSinceIso(lastSuccessAt);
  const stale = minutesSinceSuccess === null || minutesSinceSuccess > shiftStaleMinutes;

  if (shiftReadError) {
    return {
      ok: false,
      status: "error",
      message: "Lokale vaktdata kan ikke leses. Viser sist kjente vakter.",
      lastAttemptAt,
      lastSuccessAt,
      lastErrorAt: new Date().toISOString(),
      lastError: shiftReadError,
      minutesSinceSuccess,
      staleMinutes: shiftStaleMinutes,
    };
  }

  if (metaStatus === "error" || lastError) {
    return {
      ok: false,
      status: "error",
      message: "Excel-arket kan ikke hentes. Viser sist kjente vakter.",
      lastAttemptAt,
      lastSuccessAt,
      lastErrorAt,
      lastError,
      minutesSinceSuccess,
      staleMinutes: shiftStaleMinutes,
    };
  }

  if (stale) {
    return {
      ok: false,
      status: "stale",
      message: "Excel-vaktene er ikke oppdatert i tide. Viser sist kjente vakter.",
      lastAttemptAt,
      lastSuccessAt,
      lastErrorAt,
      lastError,
      minutesSinceSuccess,
      staleMinutes: shiftStaleMinutes,
    };
  }

  return {
    ok: true,
    status: metaStatus === "syncing" ? "syncing" : "ok",
    message: "Excel-sync OK",
    lastAttemptAt,
    lastSuccessAt,
    lastErrorAt,
    lastError,
    minutesSinceSuccess,
    staleMinutes: shiftStaleMinutes,
  };
}

let buses = [];
let busError = null;
let weather = null;
let weatherError = null;
let calendarEvents = [];
let calendarErrors = [];
let calendarUpdatedAt = null;
let todos = [];
let todoError = null;
let todoUpdatedAt = null;
let training = null;
let trainingError = null;
let trainingUpdatedAt = null;
let exam = null;
let examError = null;
let examUpdatedAt = null;
const shiftStatus = buildShiftStatus();
try {
  buses = await fetchBusDepartures();
} catch (error) {
  busError = error instanceof Error ? error.message : String(error);
}

try {
  weather = await fetchWeather(previousSnapshot);
} catch (error) {
  weatherError = error instanceof Error ? error.message : String(error);
  weather = previousSnapshot?.weather ?? null;
}

try {
  const calendar = await fetchCalendarEvents(previousSnapshot);
  calendarEvents = calendar.events;
  calendarUpdatedAt = calendar.updatedAt;
  calendarErrors = calendar.errors;
} catch (error) {
  calendarErrors = [error instanceof Error ? error.message : String(error)];
  calendarEvents = previousSnapshot?.calendarEvents ?? [];
  calendarUpdatedAt = previousSnapshot?.calendarUpdatedAt ?? null;
}

try {
  todos = await fetchTodoistTasks();
  todoUpdatedAt = new Date().toISOString();
} catch (error) {
  todoError = error instanceof Error ? error.message : String(error);
  todos = previousSnapshot?.todos ?? [];
  todoUpdatedAt = previousSnapshot?.todoUpdatedAt ?? null;
}

try {
  const trainingSummary = buildTrainingSummary(previousSnapshot);
  training = trainingSummary.training;
  trainingUpdatedAt = trainingSummary.updatedAt;
  trainingError = trainingSummary.error;
} catch (error) {
  trainingError = error instanceof Error ? error.message : String(error);
  training = previousSnapshot?.training ?? null;
  trainingUpdatedAt = previousSnapshot?.trainingUpdatedAt ?? null;
}

try {
  const examSummary = buildExamSummary(previousSnapshot);
  exam = examSummary.exam;
  examUpdatedAt = examSummary.updatedAt;
  examError = examSummary.error;
} catch (error) {
  examError = error instanceof Error ? error.message : String(error);
  exam = previousSnapshot?.exam ?? null;
  examUpdatedAt = previousSnapshot?.examUpdatedAt ?? null;
}

const snapshot = {
  updatedAt: new Date().toISOString(),
  shiftSyncAt: cleanMeta(meta.last_success_at) ?? cleanMeta(meta.last_sync_at) ?? previousSnapshot?.shiftSyncAt ?? null,
  shiftStatus,
  person: cleanMeta(meta.person) ?? previousSnapshot?.person ?? "Marius V",
  busError,
  buses,
  weatherError,
  weather,
  calendarUpdatedAt,
  calendarErrors,
  calendarEvents,
  todoUpdatedAt,
  todoError,
  todos,
  trainingUpdatedAt,
  trainingError,
  training,
  examUpdatedAt,
  examError,
  exam,
  shifts,
};

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, `${JSON.stringify(snapshot, null, 2)}\n`);
console.log(
  `Wrote ${shifts.length} shifts, ${calendarEvents.length} calendar events, ${
    todos.length
  } todos, ${training ? "training" : "no training"}, ${exam ? "exam" : "no exam"}, ${
    buses.length
  } bus departures and ${
    weather ? "weather" : "no weather"
  } to ${outPath}`,
);
