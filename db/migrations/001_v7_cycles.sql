-- Migration: 001_v7_cycles.sql
-- Description: Foundation for Investment Cycles v7 (Titan-OMNI)
-- Author: Antigravity (Assistant)
-- Date: 2026-02-12

-- 1. Enable required extensions
create extension if not exists pgcrypto;

-- 2. Table: investment_cycles
create table if not exists investment_cycles (
    cycle_id uuid primary key default gen_random_uuid(),
    status text not null check (status in ('ACTIVE', 'FINISHING', 'STOP')),
    created_at timestamptz not null default now(),
    started_at timestamptz null,
    finished_at timestamptz null,
    base_capital numeric not null check (base_capital > 0),
    current_capital numeric not null check (current_capital >= 0),
    realized_pnl numeric not null default 0,
    withdrawn_profit numeric not null default 0,
    notes text null
);

-- 3. Table: cycle_events
-- Note: Append-only enforcement will be handled via API in future steps.
create table if not exists cycle_events (
    id bigserial primary key,
    cycle_id uuid references investment_cycles(cycle_id),
    ts timestamptz not null default now(),
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    actor text not null default 'system'
);

-- Indexes for cycle_events
create index if not exists idx_cycle_events_cycle_id on cycle_events(cycle_id);
create index if not exists idx_cycle_events_ts on cycle_events(ts);

-- 4. Table: governance_requests
create table if not exists governance_requests (
    id bigserial primary key,
    ts timestamptz not null default now(),
    request_type text not null check (request_type in ('START_CYCLE', 'FINISH_CYCLE', 'EMERGENCY_STOP')),
    cycle_id uuid null,
    requested_by text not null default 'user',
    status text not null default 'PENDING' check (status in ('PENDING', 'APPLIED', 'REJECTED')),
    reason text null
);

-- Indexes for governance_requests
create index if not exists idx_governance_requests_status on governance_requests(status);
create index if not exists idx_governance_requests_request_type on governance_requests(request_type);
create index if not exists idx_governance_requests_cycle_id on governance_requests(cycle_id);
