CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS complaints (
    id                  SERIAL PRIMARY KEY,

    -- Identity fields (NOT NULL theo yêu cầu)
    cmplid              CHAR(9)     NOT NULL,
    odino               CHAR(9)     NOT NULL,
    mfr_name            VARCHAR(40),

    -- Vehicle / equipment info
    maketxt             VARCHAR(25),
    modeltxt            VARCHAR(256),
    yeartxt             CHAR(4),
    crash               CHAR(1),
    faildate            DATE,
    faildate_raw_invalid       TEXT,
    fire                CHAR(1),
    injured             NUMERIC(10, 2),
    deaths              NUMERIC(10, 2),
    compdesc            TEXT,
    city                VARCHAR(30),
    state               CHAR(2),
    vin                 CHAR(11),

    datea               DATE,
    datea_raw_invalid          TEXT,
    ldate               DATE,
    ldate_raw_invalid          TEXT,

    miles               NUMERIC(10, 2),
    occurences          NUMERIC(10, 2),
    cdescr              TEXT,
    cmpl_type           VARCHAR(4),
    police_rpt_yn       CHAR(1),

    purch_dt            DATE,
    purch_dt_raw_invalid       TEXT,

    orig_owner_yn       CHAR(1),
    anti_brakes_yn      CHAR(1),
    cruise_cont_yn      CHAR(1),
    num_cyls            NUMERIC(10, 2),
    drive_train         VARCHAR(4),
    fuel_sys            VARCHAR(4),
    fuel_type           VARCHAR(4),
    trans_type          VARCHAR(4),
    veh_speed           NUMERIC(10, 2),

    dot                 VARCHAR(20),
    tire_size           VARCHAR(30),
    loc_of_tire         VARCHAR(4),
    tire_fail_type      VARCHAR(4),
    orig_equip_yn       CHAR(1),

    manuf_dt            DATE,
    manuf_dt_raw_invalid       TEXT,

    seat_type           VARCHAR(4),
    restraint_type      VARCHAR(4),

    dealer_name         VARCHAR(40),
    dealer_tel          VARCHAR(20),
    dealer_city         VARCHAR(30),
    dealer_state        CHAR(2),
    dealer_zip          VARCHAR(10),

    prod_type           VARCHAR(4),
    repaired_yn         CHAR(1),
    medical_attn        CHAR(1),
    vehicles_towed_yn   CHAR(1),
    state_of_incident   CHAR(2),
    vehicle_operator    VARCHAR(40),

    -- RAG fields
    summary             TEXT NOT NULL,
    embedding           vector(768)
);

-- Index tìm kiếm theo id/complaint gốc (ODINO có thể lặp lại giữa nhiều component)
CREATE INDEX IF NOT EXISTS idx_complaints_odino ON complaints (odino);
CREATE INDEX IF NOT EXISTS idx_complaints_cmplid ON complaints (cmplid);

-- Vector index cho ANN search bằng cosine distance
CREATE INDEX IF NOT EXISTS idx_complaints_embedding
    ON complaints USING hnsw (embedding vector_cosine_ops);