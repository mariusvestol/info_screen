#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { createSign } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const appDir = dirname(fileURLToPath(import.meta.url));
const dbPath = process.env.TRAINING_DB ?? resolve(appDir, "training.db");
const keyPath = process.env.FIREBASE_SERVICE_ACCOUNT ?? resolve(appDir, "firebase-service-account.json");
const projectId = process.env.FIREBASE_PROJECT_ID ?? "swole-c26d7";
const envPath = resolve(appDir, ".env");

loadDotenv();

const userId = process.env.FIREBASE_TRAINING_USER_ID;
const firestoreScope = "https://www.googleapis.com/auth/datastore";

function loadDotenv() {
  if (!existsSync(envPath)) return;
  for (const rawLine of readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const [key, ...rest] = line.split("=");
    process.env[key.trim()] ??= rest.join("=").trim().replace(/^["']|["']$/g, "");
  }
}

function sqlString(value) {
  if (value === null || value === undefined) return "NULL";
  return `'${String(value).replaceAll("'", "''")}'`;
}

function sqlNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? String(number) : "NULL";
}

function runSql(sql) {
  const result = spawnSync("sqlite3", [dbPath], {
    encoding: "utf8",
    input: sql,
  });

  if (result.status !== 0) {
    throw new Error(result.stderr.trim() || `sqlite3 exited with ${result.status}`);
  }
}

function initDb() {
  runSql(`
    CREATE TABLE IF NOT EXISTS training_workouts (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      name TEXT NOT NULL,
      started_at TEXT,
      ended_at TEXT,
      created_at TEXT,
      total_volume REAL NOT NULL DEFAULT 0,
      exercise_count INTEGER NOT NULL DEFAULT 0,
      set_count INTEGER NOT NULL DEFAULT 0,
      top_set_exercise TEXT,
      top_set_weight REAL,
      top_set_reps INTEGER,
      top_set_volume REAL,
      payload_json TEXT NOT NULL,
      synced_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_training_workouts_user_started
      ON training_workouts(user_id, started_at);

    CREATE TABLE IF NOT EXISTS training_exercise_stats (
      user_id TEXT NOT NULL,
      exercise_name TEXT NOT NULL,
      last_workout_at TEXT,
      last_weight REAL,
      last_reps INTEGER,
      best_weight REAL,
      best_volume REAL,
      total_sets INTEGER NOT NULL DEFAULT 0,
      total_reps INTEGER NOT NULL DEFAULT 0,
      total_volume REAL NOT NULL DEFAULT 0,
      PRIMARY KEY (user_id, exercise_name)
    );

    CREATE TABLE IF NOT EXISTS training_sync_meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
  `);
}

function writeMeta(values) {
  const rows = Object.entries(values)
    .map(([key, value]) => `
      INSERT INTO training_sync_meta(key, value) VALUES(${sqlString(key)}, ${sqlString(value)})
      ON CONFLICT(key) DO UPDATE SET value = excluded.value;
    `)
    .join("\n");
  runSql(rows);
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
    scope: firestoreScope,
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

async function getAccessToken() {
  const serviceAccount = JSON.parse(readFileSync(keyPath, "utf8"));
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: signJwt(serviceAccount),
    }),
  });

  if (!response.ok) {
    throw new Error(`Firebase token ${response.status} ${await response.text()}`);
  }

  return (await response.json()).access_token;
}

function decodeFirestoreValue(value) {
  if (!value || typeof value !== "object") return null;
  if ("stringValue" in value) return value.stringValue;
  if ("integerValue" in value) return Number(value.integerValue);
  if ("doubleValue" in value) return Number(value.doubleValue);
  if ("booleanValue" in value) return value.booleanValue;
  if ("timestampValue" in value) return value.timestampValue;
  if ("nullValue" in value) return null;
  if ("arrayValue" in value) return (value.arrayValue.values ?? []).map(decodeFirestoreValue);
  if ("mapValue" in value) {
    return Object.fromEntries(
      Object.entries(value.mapValue.fields ?? {}).map(([key, child]) => [
        key,
        decodeFirestoreValue(child),
      ]),
    );
  }
  return null;
}

function decodeFirestoreDocument(document) {
  return {
    id: document.name.split("/").pop(),
    ...decodeFirestoreValue({ mapValue: { fields: document.fields ?? {} } }),
  };
}

async function fetchWorkouts() {
  const token = await getAccessToken();
  const baseUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents`;
  const workouts = [];
  let pageToken = null;

  do {
    const params = new URLSearchParams({ pageSize: "100" });
    if (pageToken) params.set("pageToken", pageToken);
    const url = `${baseUrl}/users/${encodeURIComponent(userId)}/workouts?${params}`;
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error(`Firestore workouts ${response.status} ${await response.text()}`);
    }

    const payload = await response.json();
    workouts.push(...(payload.documents ?? []).map(decodeFirestoreDocument));
    pageToken = payload.nextPageToken ?? null;
  } while (pageToken);

  return workouts.sort((a, b) => String(b.startedAt ?? "").localeCompare(String(a.startedAt ?? "")));
}

function workoutStats(workout) {
  const exercises = Array.isArray(workout.exercises) ? workout.exercises : [];
  const doneSets = exercises.flatMap((exercise) =>
    (Array.isArray(exercise.sets) ? exercise.sets : [])
      .filter((set) => set.done !== false)
      .map((set) => ({
        exercise: exercise.name ?? "Ukjent",
        reps: Number(set.reps ?? 0),
        weight: Number(set.weight ?? 0),
      }))
      .filter((set) => Number.isFinite(set.reps) && Number.isFinite(set.weight)),
  );
  const topSet =
    doneSets
      .map((set) => ({ ...set, volume: set.reps * set.weight }))
      .sort((a, b) => b.volume - a.volume || b.weight - a.weight)[0] ?? null;

  return {
    exerciseCount: exercises.length,
    setCount: doneSets.length,
    topSet,
  };
}

function aggregateExerciseStats(workouts) {
  const stats = new Map();
  const ascending = [...workouts].sort((a, b) =>
    String(a.startedAt ?? "").localeCompare(String(b.startedAt ?? "")),
  );

  for (const workout of ascending) {
    const exercises = Array.isArray(workout.exercises) ? workout.exercises : [];
    for (const exercise of exercises) {
      const name = exercise.name ?? "Ukjent";
      const sets = (Array.isArray(exercise.sets) ? exercise.sets : [])
        .filter((set) => set.done !== false)
        .map((set) => ({
          reps: Number(set.reps ?? 0),
          weight: Number(set.weight ?? 0),
        }))
        .filter((set) => Number.isFinite(set.reps) && Number.isFinite(set.weight));
      if (!sets.length) continue;

      const current =
        stats.get(name) ?? {
          exerciseName: name,
          lastWorkoutAt: null,
          lastWeight: null,
          lastReps: null,
          bestWeight: 0,
          bestVolume: 0,
          totalSets: 0,
          totalReps: 0,
          totalVolume: 0,
        };
      const topSet = sets
        .map((set) => ({ ...set, volume: set.weight * set.reps }))
        .sort((a, b) => b.weight - a.weight || b.volume - a.volume)[0];

      current.lastWorkoutAt = workout.startedAt ?? workout.createdAt ?? null;
      current.lastWeight = topSet.weight;
      current.lastReps = topSet.reps;
      current.bestWeight = Math.max(current.bestWeight, ...sets.map((set) => set.weight));
      current.bestVolume = Math.max(
        current.bestVolume,
        ...sets.map((set) => set.weight * set.reps),
      );
      current.totalSets += sets.length;
      current.totalReps += sets.reduce((sum, set) => sum + set.reps, 0);
      current.totalVolume += sets.reduce((sum, set) => sum + set.weight * set.reps, 0);
      stats.set(name, current);
    }
  }

  return [...stats.values()].sort((a, b) => b.totalVolume - a.totalVolume);
}

function saveWorkouts(workouts) {
  const now = new Date().toISOString();
  const workoutRows = workouts
    .map((workout) => {
      const stats = workoutStats(workout);
      const topSet = stats.topSet;
      return `
        INSERT INTO training_workouts (
          id, user_id, name, started_at, ended_at, created_at, total_volume,
          exercise_count, set_count, top_set_exercise, top_set_weight,
          top_set_reps, top_set_volume, payload_json, synced_at
        ) VALUES (
          ${sqlString(workout.id)},
          ${sqlString(userId)},
          ${sqlString(workout.name ?? "Økt")},
          ${sqlString(workout.startedAt ?? null)},
          ${sqlString(workout.endedAt ?? null)},
          ${sqlString(workout.createdAt ?? null)},
          ${sqlNumber(workout.totalVolume ?? 0)},
          ${sqlNumber(stats.exerciseCount)},
          ${sqlNumber(stats.setCount)},
          ${sqlString(topSet?.exercise ?? null)},
          ${sqlNumber(topSet?.weight ?? null)},
          ${sqlNumber(topSet?.reps ?? null)},
          ${sqlNumber(topSet?.volume ?? null)},
          ${sqlString(JSON.stringify(workout))},
          ${sqlString(now)}
        )
        ON CONFLICT(id) DO UPDATE SET
          user_id = excluded.user_id,
          name = excluded.name,
          started_at = excluded.started_at,
          ended_at = excluded.ended_at,
          created_at = excluded.created_at,
          total_volume = excluded.total_volume,
          exercise_count = excluded.exercise_count,
          set_count = excluded.set_count,
          top_set_exercise = excluded.top_set_exercise,
          top_set_weight = excluded.top_set_weight,
          top_set_reps = excluded.top_set_reps,
          top_set_volume = excluded.top_set_volume,
          payload_json = excluded.payload_json,
          synced_at = excluded.synced_at;
      `;
    })
    .join("\n");

  const exerciseRows = aggregateExerciseStats(workouts)
    .map((stat) => `
      INSERT INTO training_exercise_stats (
        user_id, exercise_name, last_workout_at, last_weight, last_reps,
        best_weight, best_volume, total_sets, total_reps, total_volume
      ) VALUES (
        ${sqlString(userId)},
        ${sqlString(stat.exerciseName)},
        ${sqlString(stat.lastWorkoutAt)},
        ${sqlNumber(stat.lastWeight)},
        ${sqlNumber(stat.lastReps)},
        ${sqlNumber(stat.bestWeight)},
        ${sqlNumber(stat.bestVolume)},
        ${sqlNumber(stat.totalSets)},
        ${sqlNumber(stat.totalReps)},
        ${sqlNumber(stat.totalVolume)}
      )
      ON CONFLICT(user_id, exercise_name) DO UPDATE SET
        last_workout_at = excluded.last_workout_at,
        last_weight = excluded.last_weight,
        last_reps = excluded.last_reps,
        best_weight = excluded.best_weight,
        best_volume = excluded.best_volume,
        total_sets = excluded.total_sets,
        total_reps = excluded.total_reps,
        total_volume = excluded.total_volume;
    `)
    .join("\n");

  runSql(`
    BEGIN;
    DELETE FROM training_workouts WHERE user_id = ${sqlString(userId)};
    DELETE FROM training_exercise_stats WHERE user_id = ${sqlString(userId)};
    ${workoutRows}
    ${exerciseRows}
    COMMIT;
  `);

  writeMeta({
    status: "ok",
    user_id: userId,
    last_success_at: now,
    last_error: "",
    workout_count: String(workouts.length),
  });
}

async function main() {
  initDb();
  writeMeta({
    status: "syncing",
    user_id: userId ?? "",
    last_attempt_at: new Date().toISOString(),
  });

  if (!userId) {
    throw new Error("Missing FIREBASE_TRAINING_USER_ID in .env");
  }
  if (!existsSync(keyPath)) {
    throw new Error(`Missing Firebase service account: ${keyPath}`);
  }

  const workouts = await fetchWorkouts();
  saveWorkouts(workouts);
  console.log(`OK: synced ${workouts.length} workouts for ${userId} to ${dbPath}`);
}

try {
  await main();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  try {
    initDb();
    writeMeta({
      status: "error",
      user_id: userId ?? "",
      last_error_at: new Date().toISOString(),
      last_error: message.slice(0, 500),
    });
  } catch {
    // Keep the original sync error as the process result.
  }
  console.error(`Feil: ${message}`);
  process.exit(1);
}
