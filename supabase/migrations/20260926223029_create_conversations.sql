create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  prompt text not null,
  answer text not null,
  model_used text,
  created_at timestamptz not null default now()
);

create index if not exists conversations_user_id_created_at_idx
  on public.conversations (user_id, created_at desc);

alter table public.conversations enable row level security;

create policy "users can select own conversations"
  on public.conversations
  for select
  to authenticated
  using (auth.uid() = user_id);

create policy "users can insert own conversations"
  on public.conversations
  for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "users can delete own conversations"
  on public.conversations
  for delete
  to authenticated
  using (auth.uid() = user_id);
