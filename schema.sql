-- ----------------------------------------------------------
-- CLEANUP: Clear any partially created tables
-- ----------------------------------------------------------
drop table if exists loi_requests cascade;
drop table if exists optimizer_outputs cascade;
drop table if exists test_results cascade;
drop table if exists formulations cascade;
drop table if exists literature_reference cascade;

-- ----------------------------------------------------------
-- 1. FEEDSTOCK COMPOSITION (Parent table for ML vectors)
-- ----------------------------------------------------------
create table formulations (
    formulation_id          uuid primary key default gen_random_uuid(),
    created_at              timestamptz not null default now(),
    created_by              uuid references auth.users(id),
    cassava_waste_pct       numeric(5,2) not null check (cassava_waste_pct >= 0),
    spent_grain_pct         numeric(5,2) not null check (spent_grain_pct >= 0),
    palm_kernel_ash_pct     numeric(5,2) not null check (palm_kernel_ash_pct >= 0),
    plasticizer_pct         numeric(5,2) not null check (plasticizer_pct >= 0),
    binder_pct              numeric(5,2) not null check (binder_pct >= 0),
    moisture_content_pct    numeric(5,2),
    particle_size_um        numeric(8,2),
    processing_temp_c       numeric(6,2),
    constraint composition_sums_to_100 check (
        cassava_waste_pct + spent_grain_pct + palm_kernel_ash_pct
        + plasticizer_pct + binder_pct between 99.0 and 101.0
    )
);

-- ----------------------------------------------------------
-- 2. LITERATURE REFERENCE BENCHMARKS (Seed table)
-- ----------------------------------------------------------
create table literature_reference (
    record_id               text primary key,
    feedstock_primary       text not null,
    feedstock_secondary     text,
    binder_plasticizer      text,
    filler_loading_wt_pct    numeric(5,2),
    property_tested          text not null,
    astm_iso_standard         text not null,
    measured_value            numeric(12,4),
    unit                       text,
    value_range_low            numeric(12,4),
    value_range_high           numeric(12,4),
    elongation_pct              numeric(5,2),
    notes                       text,
    citation_url                text not null
);

-- ----------------------------------------------------------
-- 3. EMPIRICAL LAB TEST RESULTS (Child table)
-- ----------------------------------------------------------
create table test_results (
    result_id               uuid primary key default gen_random_uuid(),
    formulation_id          uuid not null references formulations(formulation_id) on delete cascade,
    created_at              timestamptz not null default now(),
    property_tested         text not null check (property_tested in (
                                'tensile_strength', 'elongation',
                                'heat_deflection_temp', 'wvtr',
                                'marine_degradability'
                            )),
    astm_standard           text not null,
    iso_equivalent          text,
    measured_value          numeric(12,4) not null,
    unit                    text not null,
    lab_name                text,
    tested_at               date,
    source_type             text not null default 'lab_measured'
                            check (source_type in ('lab_measured', 'literature_estimate')),
    citation_url            text
);

-- ----------------------------------------------------------
-- 4. INVERSE OPTIMIZER OUTPUTS (Trade-Secret Protected)
-- ----------------------------------------------------------
create table optimizer_outputs (
    output_id               uuid primary key default gen_random_uuid(),
    user_id                 uuid not null references auth.users(id),
    created_at              timestamptz not null default now(),
    target_hdt_c             numeric(6,2),
    target_wvtr              numeric(10,2),
    target_marine_days       integer,
    recommended_formulation  jsonb not null,
    tier                     text not null default 'free' check (tier in ('free','paid','enterprise'))
);

-- ----------------------------------------------------------
-- 5. B2B PILOT VALIDATION & LOI AUDIT LOG
-- ----------------------------------------------------------
create table loi_requests (
    loi_id                  uuid primary key default gen_random_uuid(),
    created_at              timestamptz not null default now(),
    company_name             text not null,
    contact_email            text not null,
    country                  text,
    requested_formulation_id uuid references formulations(formulation_id) on delete set null,
    requested_optimizer_output_id uuid references optimizer_outputs(output_id) on delete set null,
    pilot_batch_size_kg       numeric(10,2),
    status                    text not null default 'submitted'
                              check (status in ('submitted','reviewed','sample_sent','signed','declined')),
    eoi_signed_at             timestamptz,
    notes                     text
);

-- Row Level Security (RLS)
alter table optimizer_outputs enable row level security;

create policy "Users read only their own optimizer outputs"
    on optimizer_outputs for select
    using (auth.uid() = user_id);

create policy "Only paid/enterprise tier can insert optimizer outputs"
    on optimizer_outputs for insert
    with check (
        auth.uid() = user_id
        and tier in ('paid', 'enterprise')
    );

-- Indexes
create index idx_test_results_formulation on test_results(formulation_id);
create index idx_test_results_property on test_results(property_tested);
create index idx_literature_property on literature_reference(property_tested);
create index idx_loi_status on loi_requests(status);
