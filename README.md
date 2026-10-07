# 젤다의 전설 4개의 검 25주년 에디션 (DSi) 한글 패치

*The Legend of Zelda: Four Swords Anniversary Edition* (DSiWare, 북미판 `KQ9E`) 비공식 한국어 팬 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

**제작: arqhive** · **최신 버전: [v1.2f](https://github.com/arqhive/zelda-four-swords-anniversary-edition-kor-patch/releases/tag/v1.2f)** (완성판)

- 대사·안내문·시스템 메시지를 한글화했습니다(220개 항목 중 스태프 롤을 뺀 215개).
- 게임 폰트에 한글 글리프를 추가했습니다.
- 게임 제목 로고, 메뉴 버튼과 안내 문구, 스테이지 이름판 그래픽을 한글화했습니다.

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 본인이 직접 덤프한 북미판 DSiWare 원본(복호화한 `.nds` 또는 `.app`). 다른 지역판이나 이전 한글 패치본에는 적용할 수 없습니다.
- BPS 패치 도구. [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/)나 Floating IPS를 쓰면 됩니다.

### 적용 방법

1. [배포 페이지](https://github.com/arqhive/zelda-four-swords-anniversary-edition-kor-patch/releases/tag/v1.2f)에서 `KQ9E_KPatch_v1.2f.zip`을 받습니다.
2. 북미판 원본에 `KQ9E_KPatch_v1.2f.bps`를 적용합니다. 확장자가 `.app`이면 결과 파일을 `.nds`로 바꿉니다.
3. 결과 파일의 확인값을 아래 표와 비교합니다.
4. 3DS나 DSi에서는 TWiLight Menu++로 실행합니다. 한글은 영어 대사 자리에 들어 있으므로 TWiLight Menu++의 게임 언어를 English로 설정합니다.
5. melonDS에서는 DSi 모드(Full BIOS Boot 끔)로 에뮬레이터 NAND에 Unlaunch를 설치하고, Manage DSi titles에서 패치한 롬과 원본 덤프의 TMD를 Import한 뒤 Boot firmware 중 A+B를 눌러 Unlaunch 메뉴에서 실행합니다. 롬을 직접 열거나 TWiLight Menu++로 실행하면 흰 화면에서 멈춥니다.

패치한 파일은 헤더 서명이 원본과 달라 순정 DSi 메뉴에서는 실행되지 않습니다.
자세한 방법은 [`README_한국어.txt`](release/README_한국어.txt)를 참고하세요.

### 파일 확인값

| 항목 | 원본 북미판 (DSiWare, 복호화) | 패치 적용 결과 (v1.2f) |
|---|---|---|
| 크기 | 14,496,768 바이트 | 14,496,768 바이트 |
| CRC32 | `0EEE2777` | `4AE68C07` |
| MD5 | `e7223ec76a60804205a3ec41bd8a563a` | `e99a33eecf80b05b062d957fdd05d2a6` |
| SHA-1 | `e0a0086df319f4a921111083fbea18a66527a801` | `38641e22cf007678461570fcc6cac8cfb5f451a9` |

원본 파일명 예: `00000000` 또는 `00000000.app`

### 실행 환경

- **확인함**: 3DS + TWiLight Menu++, melonDS(DSi 모드 + Unlaunch).

### 알려진 문제

- `YOU` 그래픽은 영문 그대로 두었습니다. 「너」나 「당신」으로 옮기면 어색해서 일부러 남긴 것입니다.
- 스태프 롤과 게임 내 도움말 페이지는 원문 그대로입니다.
- 문 고르는 화면의 `CHOOSE A DOOR` 띠는 영문 그대로입니다. 이 그래픽은 글자 조각이 잘게 쪼개진 채 흩어져 저장되어 있고, 어느 조각이 화면 어디에 놓이는지 적힌 배치표를 찾지 못해 손대지 못했습니다.
- 한글 글꼴을 작은 칸에 맞췄기 때문에 일부 글자가 좁게 보일 수 있습니다.
- **「다 함께 놀기」(멀티플레이)는 실제로 플레이해 보지 못했습니다.** 함께 할 사람을 구하지 못해, 메뉴 그래픽은 화면으로 확인했지만 통신 중에 나오는 글은 실제 진행으로 검수하지 못했습니다.
- 스테이지 이름판 왼쪽 구석에는 판에서 떨어져 나온 낱개 픽셀이 있습니다. 원본 그래픽부터 판과 분리되어 있는 장식이라 그대로 두었고, 한글 이름판에서는 그 부분이 조금 이질적으로 보일 수 있습니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3.10 이상, [Pillow](https://pypi.org/project/pillow/).
- 원본 롬(위 확인값과 일치하는 파일).
- Windows의 **굴림(`gulim.ttc`)** 폰트. 한글 글리프를 이 폰트로 렌더링하므로 다른 환경이나 폰트 버전에서는 결과 해시가 달라질 수 있습니다.

### 빌드

```bash
python tools/build_ko.py --rom path/to/00000000 --out work/KQ9E_ko.nds
python tools/bps.py create path/to/00000000 work/KQ9E_ko.nds work/patch.bps
```

`build_ko.py`는 다음을 수행합니다.

1. `translation/ko.json`의 한국어 대사를 `us.kmsg`의 영어 칸에 넣습니다.
2. 필요한 한글 글리프를 `font_ltn.nftr`에 추가합니다.
3. `patches/gfx/*.bps`로 메뉴·이름판·로고 그래픽 파일(`subtask_us_en.cmp`, `zeldat_us_en.bin`, `subtask.cmp`)을 교체합니다.
4. 쓰지 않는 `all.kmsg`를 비워 공간을 확보하고 파일을 재배치합니다.
5. DSi 다이제스트(해시 테이블)를 다시 계산합니다.

소스 빌드 결과는 v1.2f 배포본과 NitroFS 파일 25개의 내용이 모두 같습니다. 다만 파일 배치와 빈 공간에 남은 데이터가 달라 전체 롬 해시는 배포본과 다를 수 있습니다. 로고 원본 이미지를 따로 준비할 필요는 없습니다.

### 번역 수정

- 대사: [`translation/ko.json`](translation/ko.json). `{"항목번호": "한국어 markup"}` 형식입니다.
- 제어 코드는 `{br}`(줄바꿈), `{wait:N}`, `{c2:N}` 같은 태그로 표기하며, 원문의 태그를 유지해야 합니다.
- 원문 확인: `python tools/export_script.py --rom path/to/00000000`을 실행하면 `work/translation/script.json`이 만들어집니다. 원문이므로 커밋하지 않습니다.
- 용어는 [`translation/glossary.md`](translation/glossary.md)를 따릅니다.

### 폴더 구조

```
release/       배포용 BPS 패치와 사용자 설명서
translation/   한국어 번역(ko.json), 용어집
patches/gfx/   한글 그래픽 파일용 BPS 패치
tools/         빌드 도구(NitroFS, KMSG, NFTR, LZ11/BLZ, BPS, 다이제스트)
tools/dev/     그래픽 한글화 도구(이름판·버튼 문구 재작성, UI 롬 빌드)
docs/          기술 문서, 릴리즈 노트 사본(docs/releases/)
```

### 기술 문서

파일 형식, 무결성 검사 우회, 압축기 주의점, 그래픽 작업 방법은 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)에 정리했습니다.
v1.1 제목 로고 스프라이트 누락의 원인과 수정 내용은 [`docs/TITLE_LOGO_FIX.md`](docs/TITLE_LOGO_FIX.md)에 있습니다.
그래픽 한글화에 쓴 도구는 [`tools/dev/`](tools/dev/)에 있습니다. `build_ui_rom.py` 하나로 이름판·버튼 문구를 다시 그려 롬까지 만듭니다.

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드, 한국어 번역문, 문서: [MIT License](LICENSE) (© 2026 arqhive).

## 면책

비공식 팬 번역이며 Nintendo 및 GREZZO와 관련이 없습니다. 「젤다의 전설」 관련 상표·저작권은 Nintendo에 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.
