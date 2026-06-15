alter table public.solved_problems
  add column if not exists is_daily_bite_pointer boolean not null default false,
  add column if not exists daily_bite_last_shown_at timestamptz;

create unique index if not exists solved_problems_single_daily_bite_pointer
  on public.solved_problems (is_daily_bite_pointer)
  where is_daily_bite_pointer;
