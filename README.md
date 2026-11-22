# choc-split-60 ⌨️

로우스태거(row‑staggered) 60% 배열을 좌우로 나눈 **65키 스플릿 키보드**입니다.
Kailh **Choc v1 로우프로파일 핫스왑**, 좌우 각각 **RP2040 Pro Micro**, TRRS 4극 케이블 통신,
`COL2ROW` 매트릭스를 사용합니다. 모든 PCB 배선은 자동 라우터 없이 좌표를 계산해 직접 배선했고,
`scripts/verify_pcb.py`로 전수 검증합니다.

![left](docs/preview-left.png)
![right](docs/preview-right.png)

*(빨강 = F.Cu, 파랑 = B.Cu, 흰 점 = 비아)*

---

## 1. 보드 사양

| 항목 | 값 |
|---|---|
| 배열 | 60% 로우스태거, 좌우 분리(좌 31키 / 우 34키, 합계 **65키**) |
| 키 피치 | 19.05 mm (MX 표준 피치, Choc v1 스위치/키캡 사용) |
| 행 스태거 | `0 / 0.5u / 0.75u / 1.25u` (ANSI 표준값, Tab 1.5u·Caps 1.75u·LShift 2.25u) |
| 스위치 | Kailh Choc v1 (CPG1350), **핫스왑 소켓** (`SW_Hotswap_Kailh_Choc_V1`) |
| 다이오드 | 1N4148W SOD-123 × 65, `COL2ROW` (열 → 스위치 → 다이오드 → 행) |
| MCU | RP2040 Pro Micro (Elite‑Pi / Pro Micro RP2040 호환, 24핀) × 2 |
| 좌우 연결 | TRRS PJ‑320A × 2, Full‑duplex UART (`VCC/GND/TX/RX`) |
| 리셋 | 6×6 택트 스위치 × 2 (RST–GND) |
| PCB | 2층, 1.6 mm, 좌 160×143 mm / 우 175×143 mm, M2 마운팅 홀 각 4개 |
| 펌웨어 | QMK + VIAL (RP2040, `MASTER_LEFT`) |

### 레이아웃

```
 ┌───┬───┬───┬───┬───┬───┬───┐                    ┌───┬───┬───┬───┬───┬───┬───────┐
 │ ` │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │                    │ 7 │ 8 │ 9 │ 0 │ - │ = │ BSpc  │
 ├───┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┘                    ├───┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┐
 │ Tab │ Q │ W │ E │ R │ T │                      │ Y │ U │ I │ O │ P │ [ │ ] │ \ │
 ├─────┴┬──┴┬──┴┬──┴┬──┴┬──┘                      ├───┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴───┼───┤
 │ Caps │ A │ S │ D │ F │ G                       │ H │ J │ K │ L │ ; │ ' │Enter│   │
 ├──────┴┬──┴┬──┴┬──┴┬──┴┬──┘                     ├───┴┬──┴┬──┴┬──┴┬──┴┬──┴┬────┘   │
 │ LShift│ Z │ X │ C │ V │ B                      │ N │ M │ , │ . │ / │RShift│     │
 ├───┬───┼───┼───┼───┴───┘                        ├─────┼───┼───┼───┴───┴──────┘     │
 │Ctl│Win│Alt│ Space │                            │Space│Alt│Fn │ Ctl│              │
 └───┴───┴───┴───┬───┴──┐                         └─────┴───┴───┴────┴───┐          │
                 │Th1│Th2│                                                │Th1│Th2│
                 └───┴───┘                                                └───┴───┘
```

키캡 구성: **1u × 51, 1.25u × 6, 1.5u × 1, 1.75u × 2, 2u × 3, 2.25u × 2**

---

## 2. 매트릭스와 핀맵

양쪽 PCB 모두 **6행 × 8열** 매트릭스를 쓰고, MCU 핀 배치는 좌우가 완전히 동일합니다.

### MCU 핀 → 네트 (좌/우 동일)

| 핀 | 이름 | 네트 | | 핀 | 이름 | 네트 |
|---|---|---|---|---|---|---|
| 1 | GP0 | `TX` | | 13 | RAW | – (미사용) |
| 2 | GP1 | `RX` | | 14 | GND | `GND` |
| 3 | GND | `GND` | | 15 | RST | `RST` (리셋 스위치) |
| 4 | GND | `GND` | | 16 | VCC | `VCC` (TRRS Tip) |
| 5 | GP2 | `ROW0` | | 17 | GP29 | – |
| 6 | GP3 | `ROW1` | | 18 | GP28 | – |
| 7 | GP4 | `ROW2` | | 19 | GP27 | `COL7` (좌측은 키 없음) |
| 8 | GP5 | `ROW3` | | 20 | GP26 | `COL6` |
| 9 | GP6 | `ROW4` | | 21 | GP22 | `COL4` |
| 10 | GP7 | `ROW5` | | 22 | GP20 | `COL2` |
| 11 | GP8 | `COL0` | | 23 | GP23 | `COL5` |
| 12 | GP9 | `COL1` | | 24 | GP21 | `COL3` |

### 키 → (행, 열)

| 행 \ 열 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| 0 | 좌 ` | 1 | 2 | 3 | 4 | 5 | 6 | – |
| 1 | 좌 Tab | Q | W | E | R | T | – | – |
| 2 | 좌 Caps | A | S | D | F | G | – | – |
| 3 | 좌 LShift | Z | X | C | V | B | – | – |
| 4 | 좌 LCtrl | LWin | LAlt | Space | – | – | – | – |
| 5 | – | – | – | – | Thumb1 | Thumb2 | – | – |
| 6 | 우 7 | 8 | 9 | 0 | - | = | BSpc | – |
| 7 | 우 Y | U | I | O | P | [ | ] | \ |
| 8 | 우 H | J | K | L | ; | ' | Enter | – |
| 9 | 우 N | M | , | . | / | RShift | – | – |
| 10 | 우 Space | RAlt | RFn | RCtrl | – | – | – | – |
| 11 | – | Thumb1 | Thumb2 | – | – | – | – | – |

### TRRS 배선 (좌우가 서로 반대)

| TRRS | 좌측 PCB | 우측 PCB |
|---|---|---|
| Tip | `VCC` | `VCC` |
| Ring1 | `GND` | `GND` |
| Ring2 | `TX` (GP0) | `RX` (GP1) |
| Sleeve | `RX` (GP1) | `TX` (GP0) |

> 좌측이 항상 마스터입니다(`MASTER_LEFT`). USB‑C 케이블은 **좌측**에 꽂으세요.

---

## 3. 배선 설계 규칙 (자동 라우터 미사용)

* 행(Row) 버스는 **F.Cu에 가로**로, 열(Col)은 **B.Cu에 세로**로 배선하고, 두 방향이 교차하는 지점은
  비아로 층을 바꿔 같은 층 쇼트를 만들지 않습니다.
* 신호선 **0.25 mm**, 전원(VCC/GND) **0.5 mm**, 비아 **0.6 / 0.3 mm(드릴)**.
* 동일 층 타 네트 교차 0건, 최소 클리어런스 **0.2 mm**, 보드 외곽 이격 **0.3 mm**.
* 모든 트랙은 0/45/90도. 스위치 홀·핫스왑 패드·마운팅 홀·TRRS/리셋 패드를 장애물로 계산해 회피.
* 양면 **GND 존**(F.Cu, B.Cu) + GND는 별도 트랙으로도 전부 연결(존 필 없이도 통전).
* `Edge.Cuts`는 폐곡선(4개 선분)으로 마감, 코너 여유 5 mm 이상.

---

## 4. 검증 결과

`scripts/verify_pcb.py`가 생성된 `.kicad_pcb` 파일을 **독립적으로 파싱**해 다음을 전수 검사합니다.

1. 모든 신호 네트 100% 연결(미연결 패드 0건)
2. 동일 층 타 네트 클리어런스 위반 0건 (정확한 폴리곤–세그먼트 거리 계산)
3. 스위치–다이오드 1:1 매칭, 극성(캐소드→행, 애노드→스위치) 일치
4. `Edge.Cuts` 폐곡선 및 외곽 이격
5. 트랙 0/45/90도, 최소 폭, GND 존 존재

```
$ python3 scripts/verify_pcb.py
======================================================================
checking choc-split-60-left.kicad_pcb
  pads=156 tracks=226 vias=38 nets=50
  OK: all checks passed
======================================================================
checking choc-split-60-right.kicad_pcb
  pads=168 tracks=237 vias=51 nets=54
  OK: all checks passed
```

> KiCad DRC가 아니라 자체 기하 검증입니다. 계산 근거는 `scripts/verify_pcb.py`에 그대로 들어 있습니다.
> KiCad에서 열어 `Inspect → Design Rules Checker`를 한 번 더 돌리는 것을 권장합니다.

---

## 5. BOM

| # | 수량 | 부품 | 비고 |
|---|---|---|---|
| 1 | 2 | RP2040 Pro Micro (Elite‑Pi 등) | 24핀 2.54 mm, **핀 소켓** 사용 권장 |
| 2 | 65 | Kailh Choc v1 (CPG1350) 스위치 | 로우프로파일 |
| 3 | 65 | Choc 핫스왑 소켓 | PCB 뒷면 |
| 4 | 65 | 1N4148W (SOD‑123) | 캐소드(띠) 방향 주의 |
| 5 | 2 | TRRS 잭 PJ‑320A | 3.5 mm 4극 |
| 6 | 2 | 6×6×5 mm 택트 스위치 | 리셋 |
| 7 | 8 | M2 나사/너트 | 홀 2.2 mm |
| 8 | 65 | Choc 키캡 | 1u 51 / 1.25u 6 / 1.5u 1 / 1.75u 2 / 2u 3 / 2.25u 2 |
| 9 | 5 | Choc **플레이트 마운트** 스태빌라이저 | 2u·2.25u 키용 (PCB 홀 없음) |
| 10 | 2 | PCB (2층, 1.6 mm) | 좌 160×143 / 우 175×143 mm |

배선 통계(검증 스크립트 기준)

| | 좌 | 우 |
|---|---|---|
| 트랙 | 226 세그먼트 / 약 3.0 m | 237 세그먼트 / 약 3.6 m |
| 비아 (0.6/0.3 mm) | 38 | 51 |
| 네트 | 50 | 54 |

기계 파일(`BOM.csv`)도 함께 들어 있습니다.

---

## 6. JLCPCB 발주 가이드

1. Gerber: KiCad에서 각 `.kicad_pcb`를 열고 `File → Fabrication Outputs → Gerbers`로 생성
   (2 layer, F.Cu/B.Cu + F.Mask/B.Mask + F.Silkscreen/B.Silkscreen + Edge.Cuts + 드릴 파일).
2. 두 보드는 **서로 다른 PCB**입니다. `choc-split-60-left`, `choc-split-60-right`를 각각 주문하거나,
   같은 주문에 두 파일을 넣을 경우 **패널라이징(별도 PCB로 2종 주문)** 하는 편이 안전합니다.
3. 권장 옵션
   * Layers: 2, Thickness: 1.6 mm, FR‑4
   * Min track/spacing: 0.25 mm / 0.2 mm (본 설계 최소값)
   * Min hole: 0.3 mm (비아 0.3 mm 드릴 사용)
   * Surface finish: HASL (무연)
   * Gold fingers / impedance / castellation: 없음
   * SMT 조립은 하지 않습니다(전 부품 수동 납땜, 핫스왑 소켓/다이오드/TRRS/택트만 SMD·THT).
4. 주문 전 KiCad 3D 뷰어로 **스위치·MCU·TRRS 간섭**을 한 번 확인하세요.

---

## 7. 조립

1. **뒷면(B.Cu)** 에 Choc 핫스왑 소켓 65개와 SOD‑123 다이오드 65개를 납땜합니다.
   다이오드의 **캐소드 띠가 비아(행 버스) 쪽**을 향합니다.
2. 앞면에 MCU 핀 소켓(2×12)을 납땜하고 RP2040 Pro Micro를 꽂습니다.
   **USB‑C 커넥터가 보드 바깥쪽 가장자리**를 향하도록 넣으세요(좌: 왼쪽, 우: 오른쪽).
3. TRRS 잭과 리셋 택트 스위치를 납땜합니다.
4. 스위치를 핫스왑 소켓에 꽂고, 보강판(플레이트)과 케이스를 조립합니다.
   2u/2.25u 키에는 **플레이트 마운트 Choc 스태빌라이저**를 사용합니다(PCB에는 홀 없음).
5. TRRS 케이블로 좌우를 연결하고, USB를 **좌측**에 연결합니다.

> **보강판/케이스**: 본 리포에는 케이스·보강판 도면이 없습니다. Choc 표준 컷아웃
> (14×14 mm 스위치 홀, 19.05 mm 피치, 1.6 mm 판재)으로 별도 제작하면 됩니다.
> 19.05 mm 피치는 MX 표준 피치라 Choc 키캡 사이에 1.5~2.5 mm 정도 간격이 보입니다
> (배선 공간과 표준 u 폭을 위한 선택).

> MCU를 납땜으로 PCB에 바로 붙이면 아래쪽 배선과 붙을 수 있습니다. 반드시 **핀 소켓**을 쓰세요.

---

## 8. 펌웨어 (QMK / VIAL)

```
firmware/choc_split_60/
├── choc_split_60.h      # LAYOUT 매크로(65키)
├── config.h             # 매트릭스 핀, COL2ROW, 시리얼, MASTER_LEFT
├── info.json            # QMK 메타데이터(핀, 레이아웃, split)
├── rules.mk             # SPLIT_KEYBOARD, SERIAL_DRIVER=vendor
└── keymaps/
    ├── default/keymap.c
    └── vial/{keymap.c, vial.json, config.h}
```

### QMK

```bash
git clone https://github.com/qmk/qmk_firmware
cp -r firmware/choc_split_60 qmk_firmware/keyboards/
cd qmk_firmware
qmk compile -kb choc_split_60 -km default
# 생성된 choc_split_60_default.uf2 를 RPI-RP2 드라이브에 복사
```

### VIAL

```bash
git clone https://github.com/vial-kb/vial-qmk
cp -r firmware/choc_split_60 vial-qmk/keyboards/
cd vial-qmk
make choc_split_60:vial
```

부트로더 진입: 리셋 스위치를 **두 번** 누르거나, 부팅 중 BOOT를 누른 상태로 USB 연결.

---

## 9. 리포지터리 구조

```
pcb/      choc-split-60-{left,right}.kicad_{pro,sch,pcb} + fp-lib-table
libs/     choc60.pretty (Choc 핫스왑, SOD-123, Pro Micro RP2040, TRRS, 택트, M2)
scripts/  generate_pcb.py (설계·배선 생성), verify_pcb.py (검증), preview.py, export_libs.py
docs/     preview-*.png, verification.txt
firmware/ QMK/VIAL 키보드 정의
BOM.csv, LICENSE
```

### 다시 생성하기

```bash
python3 scripts/generate_pcb.py    # 두 장의 PCB + 회로도 + 프로젝트 파일 재생성
python3 scripts/verify_pcb.py      # 기하 검증(위 4장의 결과가 다시 나옵니다)
python3 scripts/preview.py left    # 미리보기 PNG
```

`generate_pcb.py`는 KiCad 파일을 직접 쓰고, 배선은 자체 A* 라우터(0.25 mm 그리드, 45도 이동,
비아 0.6/0.3)로 계산합니다. FreeRouting 등 외부 자동 라우터는 사용하지 않습니다.

---

## 10. 크레딧

* Choc v1 / 핫스왑 풋프린트 형상: [keyswitch-kicad-library](https://github.com/perigoso/keyswitch-kicad-library) (CC‑BY‑SA‑4.0)
* TRRS PJ‑320A 풋프린트: [Keebio‑Parts](https://github.com/keebio/Keebio-Parts.pretty)
* QMK / VIAL 펌웨어

라이선스: **CC BY‑SA 4.0** (`LICENSE` 참고)
