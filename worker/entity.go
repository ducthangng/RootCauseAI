package main

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/pgvector/pgvector-go"
)

type ProcessJobMessage struct {
	JobID     string `json:"jobId"`
	Bucket    string `json:"bucket"`
	ResultKey string `json:"resultKey"`
}

// ComplaintRow — khớp 1:1 với cột CSV, đọc bằng encoding/csv hoặc gocsv.
// Giữ nguyên string vì "" (rỗng) và "9999" (unknown) đều là giá trị hợp lệ cần tự xử lý,
// không để thư viện CSV tự đoán kiểu.
type ComplaintRow struct {
	CmplID          string `csv:"CMPLID"`
	Odino           string `csv:"ODINO"`
	MfrName         string `csv:"MFR_NAME"`
	MakeTxt         string `csv:"MAKETXT"`
	ModelTxt        string `csv:"MODELTXT"`
	YearTxt         string `csv:"YEARTXT"`
	Crash           string `csv:"CRASH"`
	FailDate        string `csv:"faildate"`             // đã convert YYYY-MM-DD
	FailDateInvalid string `csv:"faildate_raw_invalid"` // giá trị gốc nếu parse lỗi
	Fire            string `csv:"FIRE"`
	Injured         string `csv:"INJURED"`
	Deaths          string `csv:"DEATHS"`
	CompDesc        string `csv:"COMPDESC"`
	City            string `csv:"CITY"`
	State           string `csv:"STATE"`
	Vin             string `csv:"VIN"`
	DateA           string `csv:"datea"`
	DateAInvalid    string `csv:"datea_raw_invalid"`
	LDate           string `csv:"ldate"`
	LDateInvalid    string `csv:"ldate_raw_invalid"`
	Miles           string `csv:"MILES"`
	Occurrences     string `csv:"OCCURENCES"`
	CDescr          string `csv:"CDESCR"`
	CmplType        string `csv:"CMPL_TYPE"`
	PoliceRptYN     string `csv:"POLICE_RPT_YN"`
	PurchDt         string `csv:"purch_dt"`
	PurchDtInvalid  string `csv:"purch_dt_raw_invalid"`
	OrigOwnerYN     string `csv:"ORIG_OWNER_YN"`
	AntiBrakesYN    string `csv:"ANTI_BRAKES_YN"`
	CruiseContYN    string `csv:"CRUISE_CONT_YN"`
	NumCyls         string `csv:"NUM_CYLS"`
	DriveTrain      string `csv:"DRIVE_TRAIN"`
	FuelSys         string `csv:"FUEL_SYS"`
	FuelType        string `csv:"FUEL_TYPE"`
	TransType       string `csv:"TRANS_TYPE"`
	VehSpeed        string `csv:"VEH_SPEED"`
	Dot             string `csv:"DOT"`
	TireSize        string `csv:"TIRE_SIZE"`
	LocOfTire       string `csv:"LOC_OF_TIRE"`
	TireFailType    string `csv:"TIRE_FAIL_TYPE"`
	OrigEquipYN     string `csv:"ORIG_EQUIP_YN"`
	ManufDt         string `csv:"manuf_dt"`
	ManufDtInvalid  string `csv:"manuf_dt_raw_invalid"`
	SeatType        string `csv:"SEAT_TYPE"`
	RestraintType   string `csv:"RESTRAINT_TYPE"`
	DealerName      string `csv:"DEALER_NAME"`
	DealerTel       string `csv:"DEALER_TEL"`
	DealerCity      string `csv:"DEALER_CITY"`
	DealerState     string `csv:"DEALER_STATE"`
	DealerZip       string `csv:"DEALER_ZIP"`
	ProdType        string `csv:"PROD_TYPE"`
	RepairedYN      string `csv:"REPAIRED_YN"`
	MedicalAttn     string `csv:"MEDICAL_ATTN"`
	VehiclesTowedYN string `csv:"VEHICLES_TOWED_YN"`
	StateOfIncident string `csv:"STATE_OF_INCIDENT"`
	VehicleOperator string `csv:"VEHICLE_OPERATOR"`
	Summary         string `csv:"summary"`
	Embedding       string `csv:"embedding"` // "[0.1,0.2,...]" — literal pgvector dạng text
}

// Complaint — domain struct để insert Postgres, kiểu dữ liệu đúng thay vì toàn string.
type Complaint struct {
	CmplID          string
	Odino           string
	MfrName         string
	MakeTxt         string
	ModelTxt        string
	YearTxt         string // giữ string vì "9999" là giá trị hợp lệ (unknown), ép sang int sẽ mất ý nghĩa đó
	Crash           *bool
	FailDate        *time.Time // nullable: null khi FailDateInvalid có giá trị
	FailDateInvalid *string    // giá trị gốc nếu parse lỗi, nil nếu hợp lệ
	Fire            *bool
	Injured         int
	Deaths          int
	CompDesc        string
	City            string
	State           string
	Vin             string
	DateA           *time.Time
	DateAInvalid    *string
	LDate           *time.Time
	LDateInvalid    *string
	Miles           int
	Occurrences     int
	CDescr          string
	CmplType        string
	PoliceRptYN     *bool
	PurchDt         *time.Time
	PurchDtInvalid  *string
	OrigOwnerYN     *bool
	AntiBrakesYN    *bool
	CruiseContYN    *bool
	NumCyls         int
	DriveTrain      string
	FuelSys         string
	FuelType        string
	TransType       string
	VehSpeed        int
	Dot             string
	TireSize        string
	LocOfTire       string
	TireFailType    string
	OrigEquipYN     *bool
	ManufDt         *time.Time
	ManufDtInvalid  *string
	SeatType        string
	RestraintType   string
	DealerName      string
	DealerTel       string
	DealerCity      string
	DealerState     string
	DealerZip       string
	ProdType        string
	RepairedYN      *bool
	MedicalAttn     *bool
	VehiclesTowedYN *bool
	StateOfIncident string
	VehicleOperator string
	Summary         string
	Embedding       []float32 // pgvector-go: pgvector.NewVector(Embedding)
}

// ── 4. Convert — phần lớn là xử lý null/rỗng ─────────────────────
func parseRow(record []string, col map[string]int) (*Complaint, error) {
	get := func(name string) string {
		if i, ok := col[name]; ok && i < len(record) {
			return strings.TrimSpace(record[i])
		}
		return ""
	}

	c := &Complaint{
		CmplID:          get("cmplid"), // KHÔNG có gạch dưới — đúng theo header thật
		Odino:           get("odino"),
		MfrName:         get("mfr_name"),
		MakeTxt:         get("maketxt"),
		ModelTxt:        get("modeltxt"),
		YearTxt:         get("yeartxt"),
		CompDesc:        get("compdesc"),
		City:            get("city"),
		State:           get("state"),
		Vin:             get("vin"),
		CDescr:          get("cdescr"),
		CmplType:        get("cmpl_type"),
		DriveTrain:      get("drive_train"),
		FuelSys:         get("fuel_sys"),
		FuelType:        get("fuel_type"),
		TransType:       get("trans_type"),
		Dot:             get("dot"),
		TireSize:        get("tire_size"),
		LocOfTire:       get("loc_of_tire"),
		TireFailType:    get("tire_fail_type"),
		SeatType:        get("seat_type"),
		RestraintType:   get("restraint_type"),
		DealerName:      get("dealer_name"),
		DealerTel:       get("dealer_tel"),
		DealerCity:      get("dealer_city"),
		DealerState:     get("dealer_state"),
		DealerZip:       get("dealer_zip"),
		ProdType:        get("prod_type"),
		StateOfIncident: get("state_of_incident"),
		VehicleOperator: get("vehicle_operator"),
		Summary:         get("summary"),
	}

	c.Crash = parseYN(get("crash"))
	c.Fire = parseYN(get("fire"))
	c.PoliceRptYN = parseYN(get("police_rpt_yn"))
	c.OrigOwnerYN = parseYN(get("orig_owner_yn"))
	c.AntiBrakesYN = parseYN(get("anti_brakes_yn"))
	c.CruiseContYN = parseYN(get("cruise_cont_yn"))
	c.OrigEquipYN = parseYN(get("orig_equip_yn"))
	c.RepairedYN = parseYN(get("repaired_yn"))
	c.MedicalAttn = parseYN(get("medical_attn"))
	c.VehiclesTowedYN = parseYN(get("vehicles_towed_yn"))

	c.Injured = parseIntOrZero(get("injured"))
	c.Deaths = parseIntOrZero(get("deaths"))
	c.Miles = parseIntOrZero(get("miles"))
	c.Occurrences = parseIntOrZero(get("occurences")) // đúng chính tả gốc NHTSA, thiếu 1 chữ "r"
	c.NumCyls = parseIntOrZero(get("num_cyls"))
	c.VehSpeed = parseIntOrZero(get("veh_speed"))

	c.FailDate, c.FailDateInvalid = parseDate(get("faildate"), get("faildate_raw_invalid"))
	c.DateA, c.DateAInvalid = parseDate(get("datea"), get("datea_raw_invalid"))
	c.LDate, c.LDateInvalid = parseDate(get("ldate"), get("ldate_raw_invalid"))
	c.PurchDt, c.PurchDtInvalid = parseDate(get("purch_dt"), get("purch_dt_raw_invalid"))
	c.ManufDt, c.ManufDtInvalid = parseDate(get("manuf_dt"), get("manuf_dt_raw_invalid"))

	if c.CmplID == "" {
		return nil, fmt.Errorf("missing cmpl_id — check header column name mapping")
	}

	emb, err := parseEmbedding(get("embedding"))
	if err != nil {
		return nil, fmt.Errorf("embedding: %w", err)
	}
	c.Embedding = emb

	return c, nil
}

// "Y" -> true, "N" -> false, rỗng/khác -> nil (unknown, KHÔNG ép về false)
func parseYN(s string) *bool {
	switch strings.ToUpper(s) {
	case "Y":
		v := true
		return &v
	case "N":
		v := false
		return &v
	default:
		return nil
	}
}
func parseIntOrZero(s string) int {
	if s == "" {
		return 0
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0 // dữ liệu NHTSA có sẵn rác kiểu " 12 " hay "N/A" ở cột số — không chặn cả dòng vì 1 cột lỗi
	}
	return n
}

// dateStr đã ở dạng YYYY-MM-DD (do bước embed xử lý trước); invalidStr là giá trị gốc nếu parse thất bại lúc đó.
func parseDate(dateStr, invalidStr string) (*time.Time, *string) {
	if invalidStr != "" {
		v := invalidStr
		return nil, &v // pipeline trước đã đánh dấu invalid — giữ nguyên, không cố parse lại
	}
	if dateStr == "" {
		return nil, nil
	}
	t, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		v := dateStr
		return nil, &v
	}
	return &t, nil
}

func parseEmbedding(s string) ([]float32, error) {
	if s == "" {
		return nil, fmt.Errorf("empty embedding")
	}
	s = strings.Trim(s, "[]")
	parts := strings.Split(s, ",")
	out := make([]float32, len(parts))
	for i, p := range parts {
		f, err := strconv.ParseFloat(strings.TrimSpace(p), 32)
		if err != nil {
			return nil, fmt.Errorf("bad float at index %d: %w", i, err)
		}
		out[i] = float32(f)
	}
	return out, nil
}

// ── 5. Insert Postgres (batch, idempotent theo cmpl_id) ───────────
func insertComplaints(ctx context.Context, rows []Complaint) error {
	pool, err := getPool(ctx)
	if err != nil {
		return err
	}

	batch := &pgx.Batch{}
	for _, c := range rows {
		batch.Queue(`
			INSERT INTO complaints (
				cmplid, odino, mfr_name, maketxt, modeltxt, yeartxt, crash,
				faildate, faildate_raw_invalid, fire, injured, deaths, compdesc,
				city, state, vin, datea, datea_raw_invalid, ldate, ldate_raw_invalid,
				miles, occurences, cdescr, cmpl_type, police_rpt_yn, purch_dt,
				purch_dt_raw_invalid, orig_owner_yn, summary, embedding
			) VALUES (
				$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
				$21,$22,$23,$24,$25,$26,$27,$28,$29,$30
			)
			ON CONFLICT (cmplid) DO UPDATE SET
				summary = EXCLUDED.summary,
				embedding = EXCLUDED.embedding
		`, // idempotent: chạy lại (do SQS at-least-once) chỉ update, không tạo dòng trùng
			c.CmplID, c.Odino, c.MfrName, c.MakeTxt, c.ModelTxt, c.YearTxt, c.Crash,
			c.FailDate, c.FailDateInvalid, c.Fire, c.Injured, c.Deaths, c.CompDesc,
			c.City, c.State, c.Vin, c.DateA, c.DateAInvalid, c.LDate, c.LDateInvalid,
			c.Miles, c.Occurrences, c.CDescr, c.CmplType, c.PoliceRptYN, c.PurchDt,
			c.PurchDtInvalid, c.OrigOwnerYN, c.Summary, pgvector.NewVector(c.Embedding),
		)
	}
	// TODO: thêm đủ các cột còn lại (anti_brakes_yn, num_cyls, dot, tire_size, ...) theo đúng schema thật của bạn —
	// tôi rút gọn ví dụ này để tránh 1 câu SQL 51 tham số khó đọc, bạn generate phần còn lại theo cùng khuôn.

	br := pool.SendBatch(ctx, batch)
	defer br.Close()
	for i := 0; i < batch.Len(); i++ {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("row %d: %w", i, err)
		}
	}
	return nil
}
