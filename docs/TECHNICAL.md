# 기술 노트

북미판 DSiWare `KQ9E` (타이틀 ID `00030004-4B513945`) 한글화 과정에서 확인한 내용입니다.

## 원본 파일
- NUS 콘텐츠 `00000000`은 복호화된 DSi SRL(.nds)이며, ARM9i/ARM7i 영역은 modcrypt 상태입니다.
- modcrypt 키: KeyX = `"Nintendo" + 게임코드 + 게임코드(역순)`, KeyY = 헤더 `0x350`, CTR = 헤더 `0x300`/`0x314`.
  (`tools/dev/decrypt_modcrypt.py`)

## NitroFS 파일
| 파일 | 내용 |
|---|---|
| `us.kmsg` | 북미판 대사 (220 항목 × 10 언어 칸, 영어 = 칸 1, 프랑스어 = 5, 스페인어 = 7) |
| `all.kmsg` | 다국어 대사 (칸 0 = 일본어 UTF-16, 후리가나 포함). 북미판 ARM9은 참조하지 않음 → 비워서 공간 확보 |
| `font_ltn.nftr` | 대사 폰트, 1bpp 10×12 셀 |
| `subtask_us_en.cmp` | LZ11 압축, NCGR 5개 + NSCR (하단 화면 UI, 스테이지 이름 바) |
| `zeldat_us_en.bin` | `(offset, size \| 0x80000000=LZ11)` 테이블, 항목 2~9 = 스테이지 지도 이름판, 7 = CHOOSE A STAGE |
| `m2dres_narc.blz`, `manpages_narc_us.blz` | BLZ(역방향 LZ) 압축 NARC |

## KMSG 형식
- 헤더 `KMSG`, 항목 수, 항목마다 `u32 flag + (offset, size) × 10`.
- 텍스트: 영어 등은 UTF-8, 일본어 칸은 UTF-16LE. 한글 UTF-8 3바이트를 그대로 표시 가능.
- 제어 코드: `0x7F` + (UTF-8은 짝수 오프셋 정렬) + `u16 cmd` + `u16 인자`.
  인자 수: `{0:0,1:0,2:1,3:1,4:0,5:1,6:0,7:1,8:1,9:1,10:1,11:1,12:1,13:3,14:0,17:1,18:0,19:0}`
- 후리가나: `{0x12} 읽기 0x0000 한자 {0x13}`.
- 문자열은 4바이트 정렬, size에는 패딩 미포함.

## NFTR
- CMAP: 0x20–0x7E, 0xA1–0xFF 직접 매핑 + scan 타입. 한글은 scan CMAP에 추가.
- 한글을 원래 10px 셀에 넣어도 정상 표시(굴림 11px 렌더링).

## 무결성 검사 (중요)
- 게임이 NitroFS 섹터를 DSi 다이제스트로 검사: HMAC-SHA1(섹터 0x400) → 블록(32섹터) → 마스터(헤더 `0x328`).
  HMAC 키는 DSi 표준 키(`21 06 C0 DE …`). 파일을 바꾸면 반드시 재계산 (`tools/fix_digest.py`).
- 마스터 해시를 바꾸면 헤더 RSA 서명이 깨져 **순정 DSi 메뉴는 실행 거부**("An error has occurred").
  → TWiLight Menu++(nds-bootstrap) 또는 Unlaunch로 실행.
- 파일 데이터는 다이제스트 섹터 테이블(`0xD3F000`) 앞에 있어야 함. 넘어가면 해시 재계산 시 데이터가 덮임.

## 압축 주의
- **게임의 LZ11 해제 루틴은 displacement 1을 제대로 처리하지 못함.** 원본 파일도 최소 거리 2.
  압축기는 거리 ≥ 2만 사용해야 함 (`tools/lz.py`). 위반 시 그래픽 노이즈 + 멈춤.
- BLZ: 푸터 `enc_len(3) | hdr_len(1) | inc_len(4)`, 쌍 바이트는 상위 바이트가 뒤쪽.

## 그래픽
- NCGR 데이터는 **8×8 타일의 연속**(행 우선 비트맵이 아님). 256px 폭 시트 = 한 줄 32타일.
- 화면의 글자는 게임 코드(셀/타일맵)가 조립하므로, 스크린샷의 8×8 블록을 색 배치 정규화로 타일과 대조해 위치를 찾음 (`tools/dev/tile_match.py`, `gfx_patch.py`).
- 함정:
  - 판 끝 장식 등 **여러 판이 공유하는 타일**에 쓰면 다른 그래픽이 깨짐 → 화면에 다른 곳에도 나오는 타일은 잠금.
  - 이웃 번호로 단색 타일을 **추측하면** 모양만 같은 다른 타일을 고르게 됨.
  - 같은 그림이 두 파일에 중복 존재(지도 이름판 = `zeldat_us_en` 항목 2, 하단 바 = `subtask_us_en` NCGR 3).
  - 판 배경은 세로 그라데이션 → 글자 틈의 원본 세로줄 패턴으로 지워야 줄무늬가 안 생김.
- 하단 바 스테이지 이름은 NCGR 3에 온전한 그림으로 있고, 지도 이름판(항목 2~9)은 같은 타일 배치를 공유.

## 테스트 환경
- melonDS: DSi 모드, Full BIOS Boot 끔. 롬 직접 부팅/TWiLight는 흰 화면(DSiWare를 카트로 인식).
  Unlaunch를 에뮬 NAND에 설치 → Manage DSi titles로 롬+TMD import → Unlaunch 메뉴에서 실행.
- 실기: 3DS CFW + TWiLight Menu++ 에서 정상 동작 확인.
