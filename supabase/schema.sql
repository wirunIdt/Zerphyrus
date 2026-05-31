create table if not exists public.zerphyrus_kv (
  name text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create or replace function public.set_zerphyrus_kv_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_zerphyrus_kv_updated_at on public.zerphyrus_kv;

create trigger trg_zerphyrus_kv_updated_at
before update on public.zerphyrus_kv
for each row
execute function public.set_zerphyrus_kv_updated_at();

alter table public.zerphyrus_kv enable row level security;

drop policy if exists "zerphyrus service role manages kv" on public.zerphyrus_kv;

create policy "zerphyrus service role manages kv"
on public.zerphyrus_kv
for all
to service_role
using (true)
with check (true);

insert into storage.buckets (id, name, public)
values ('zerphyrus-uploads', 'zerphyrus-uploads', false)
on conflict (id) do nothing;
