==============================================================
 젤다의 전설 4개의 검 25주년 에디션 (북미판 DSiWare) 한글 패치 v1.0
 The Legend of Zelda: Four Swords Anniversary Edition - Korean Patch
==============================================================

제작: arqhive
배포 파일: Zelda_4Swords_AE_KQ9E_Korean_v1.0.bps


■ 소개
--------------------------------------------------------------
닌텐도 DSiWare "젤다의 전설 4개의 검 25주년 에디션" 북미판(KQ9E)을
한국어로 즐길 수 있게 하는 비공식 팬 한글 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

- 게임 내 대사·안내문·시스템 메시지 한글화 (215개 항목)
- 한글 폰트 추가
- 주요 메뉴·타이틀 그래픽 한글화
  (시작 / 도움말 / 파일 선택 / 복사 / 삭제 / 다 함께 놀기 / 혼자 놀기 /
   색 선택 / 이름 입력 / 확인 / 스테이지 선택 / 스테이지 이름판)


■ 준비물
--------------------------------------------------------------
1) 본인이 직접 덤프한 북미판 DSiWare 원본 파일 (복호화된 .nds / .app)
   - 게임 코드: KQ9E
   - 크기 : 14,496,768 바이트
   - CRC32: 0EEE2777
   - MD5  : e7223ec76a60804205a3ec41bd8a563a
   - SHA1 : e0a0086df319f4a921111083fbea18a66527a801

   ※ 해시가 다르면 패치가 적용되지 않습니다(BPS 형식이 자동으로 검사합니다).
   ※ 게임 롬 파일은 배포하지 않습니다. 반드시 본인이 소유한 게임에서 덤프하세요.

2) 패치 적용 도구 (둘 중 하나)
   - Rom Patcher JS (웹 브라우저): https://www.marcrobledo.com/RomPatcher.js/
   - Floating IPS (Windows)


■ 패치 적용 방법
--------------------------------------------------------------
[Rom Patcher JS]
  1. 사이트 접속
  2. "ROM file"에 원본 파일 선택
  3. "Patch file"에 Zelda_4Swords_AE_KQ9E_Korean_v1.0.bps 선택
  4. "Apply patch" 클릭 → 패치된 파일 저장

[Floating IPS]
  1. flips.exe 실행 → "Apply Patch"
  2. .bps 패치 파일 선택 → 원본 파일 선택 → 저장할 이름 지정

적용 후 파일 확인값:
   - 크기 : 14,496,768 바이트
   - CRC32: 8A43970A
   - MD5  : 493f8ed1c6af1395975f4c9bf9107a8a
   - SHA1 : 6a381deaec18e6e75e22ea2c0b507df529aa6cd8

확장자가 .app 이라면 .nds 로 바꿔 사용하세요.


■ 실행 방법
--------------------------------------------------------------
[3DS / DSi 실기 - TWiLight Menu++ (확인 완료)]
  1. 패치된 .nds 파일을 SD 카드의 roms/nds 폴더 등에 복사
  2. TWiLight Menu++ 설정에서 게임 언어(Game language)를 English 로 설정
     (한글은 영어 대사 자리에 들어 있습니다)
  3. TWiLight Menu++에서 실행

[주의]
  - 패치된 파일은 헤더 서명이 원본과 달라서, 개조하지 않은 DSi 본체 메뉴에
    설치하면 "An error has occurred" 가 뜨며 실행되지 않습니다.
    TWiLight Menu++(nds-bootstrap) 또는 Unlaunch 환경에서 실행하세요.
  - melonDS 에뮬레이터에서는 롬을 직접 열거나 TWiLight Menu++로 실행하면
    흰 화면에서 멈춥니다. 아래 [melonDS] 방법을 따라 주세요.

[melonDS 에뮬레이터 (Unlaunch 경유, 확인 완료)]
  준비물
    - melonDS 1.x
    - 본인 DSi에서 덤프한 파일: DSi ARM9/ARM7 BIOS, DSi 펌웨어,
      DSi NAND(no$gba 푸터 포함). 북미(USA) 본체 NAND 권장
    - 원본 게임 덤프에 들어 있는 TMD 파일(tmd.0 등)
    - Unlaunch 설치 파일 UNLAUNCH.DSI (https://problemkaputt.de/unlaunch.htm)
    - TWiLight Menu++ DSi용 (Unlaunch 설치에만 사용)

  1) 기본 설정
     - Config > Emu settings > General: Console type = DSi
     - DSi 탭: BIOS9, BIOS7, Firmware, NAND 경로 지정
     - DSi 탭: "Full BIOS Boot" 는 반드시 끄기 (켜면 흰 화면)
     - NAND 파일은 미리 백업해 두세요.

  2) Unlaunch 설치 (최초 1회)
     - Config > Emu settings > DSi SD card: SD 카드 사용 + 폴더 동기화(Folder sync)로
       TWiLight Menu++ 파일과 UNLAUNCH.DSI 를 넣은 폴더 지정
     - General: "Boot game directly" 켜기
     - File > Open ROM 으로 SD 폴더의 BOOT.NDS(TWiLight Menu++) 실행
       (UNLAUNCH.DSI 를 직접 열면 흰 화면이 됩니다)
     - TWiLight Menu++ 파일 목록에서 UNLAUNCH.DSI 실행 > "Install now"
     - 설치가 끝나면 System > Stop

  3) 패치된 게임 설치
     - 에뮬레이션이 멈춘 상태에서 System > Manage DSi titles
       (실행 중에는 메뉴가 비활성화됩니다)
     - 같은 게임이 이미 있으면 삭제한 뒤 Import
     - 실행 파일: 패치된 .nds / TMD: 원본 덤프의 tmd 파일

  4) 실행
     - File > Boot firmware 를 누르고, 부팅되는 동안 A+B 버튼을 누르고 있기
     - Unlaunch 메뉴가 뜨면 "Zelda: Four Swords" 선택
     - 게임 언어는 DSi 본체(NAND) 언어 설정을 따릅니다. English 로 설정하세요.

  melonDS 에서 안 되는 경우
     - 흰 화면: 롬 직접 열기 / TWiLight Menu++ 에서 게임 실행 / Unlaunch 의 Launcher 항목 /
       Full BIOS Boot 켬  → 모두 이 게임이 동작하지 않는 경로입니다.
     - "An error has occurred": Unlaunch 를 거치지 않고 순정 DSi 메뉴에서 실행한 경우입니다
       (패치로 헤더 서명이 달라져 순정 메뉴는 실행을 거부합니다).


■ 알려진 문제 / 미번역 부분
--------------------------------------------------------------
- 색 선택 화면의 빨간 판 "Select Color", OK·Back 버튼은 영문으로 남아 있습니다.
- 엔딩 제작진 목록(스태프 롤)은 원문(영문) 그대로입니다.
- 시작의 사당 이외의 스테이지 이름판은 게임 화면 없이 제작하여,
  일부 화면에서 색이나 모양이 어색할 수 있습니다.
- 스테이지 선택 판 아래쪽 등에 원래 영문 그래픽의 흔적이 몇 픽셀 남는 곳이 있습니다.
- 게임 내 설명서(도움말 페이지)는 번역하지 않았습니다.
- 한글 글꼴이 작은 칸에 맞춰져 있어 일부 글자가 좁게 보일 수 있습니다.

오류나 오역 제보는 제작자(arqhive)에게 알려주세요.


■ 버전 기록
--------------------------------------------------------------
v1.0  최초 배포


■ 라이선스
--------------------------------------------------------------
패치 제작 도구·번역문은 MIT License로 공개합니다 (© 2026 arqhive).
게임 자체와 그 데이터에는 적용되지 않습니다.


■ 면책
--------------------------------------------------------------
- 이 패치는 비공식 팬 번역이며 Nintendo 및 GREZZO와 관련이 없습니다.
- 「젤다의 전설」 및 관련 상표·저작권은 Nintendo에 있습니다.
- 패치 사용으로 발생하는 문제에 대해 제작자는 책임지지 않습니다.
- 패치된 롬 파일의 재배포를 금지합니다. 패치 파일(.bps)만 배포해 주세요.
