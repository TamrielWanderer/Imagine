; Extra shortcut bars for the ReIMAGINE client (ImagineClient.exe 2020-12-17).
; Assembled with: nasm -f bin shortcut_bars.asm -o shortcut_bars.bin
; The code lives in a large int3 padding run of .text at CODE_VA; the
; variables live in the unused tail of the .data section at DATA_VA.
; See build_shortcut_bars.py and docs/client-shortcut-bars-notes.md.

bits 32
org 0x1400000

; ---- game functions -------------------------------------------------------
GETWIN      equ 0xd91ad0    ; cdecl  window* (int id)
CREATEWIN   equ 0xd85600    ; cdecl  int id (type, 0, 0, unique)
W_LAYOUT    equ 0xded1b0    ; this   (int layout)            ret 4
W_SETMAX    equ 0xdedb80    ; this   (int maxPages)          ret 4
W_SETPAGE   equ 0xdedbb0    ; this   (int page)              ret 4
W_DRAWSLOT  equ 0xded5a0    ; this   (int slot, int page)    ret 8
TASK_INIT2  equ 0x6cc3e0    ; this   ()  layout + push all slots
KEYPOLL     equ 0x6d2cb0    ; this   ()  polls ShortCut* key actions
USESLOT     equ 0x6d1cb0    ; this   (int page, int slot)    ret 8
DROPEXT     equ 0x6d4050    ; this   (5 args)                ret 0x14
ISPRESSED   equ 0x498d00    ; cdecl  bool (int action, int)
NEW         equ 0x10d09f4   ; cdecl  void* (size)
ACT_CTOR    equ 0x42671f    ; this   (id, name, key, flag)   ret 0x10
MAP_INDEX   equ 0x4034e5    ; this   Action** (const int*)   ret 4

I_FOPEN     equ 0x87eabd8
I_FCLOSE    equ 0x87eabd0
I_FPRINTF   equ 0x87eabd4
I_FGETS     equ 0x87eabf8
I_SSCANF    equ 0x87eab80
I_TICK      equ 0x87ea58c

SHORTCUT_WINDOW equ 0x159
SLOT_SIZE   equ 0x824
SLOTS       equ 24
PAGES       equ 10
MAXBARS     equ 6
ACTION_BASE equ 0x88        ; first new key action id (game uses up to 0x87)

; ---- variables (.data tail) -----------------------------------------------
DATA_VA     equ 0x87e8e80
g_this      equ DATA_VA + 0x00   ; window seen at SetSlot entry
g_task      equ DATA_VA + 0x04
g_mainid    equ DATA_VA + 0x08
g_loaded    equ DATA_VA + 0x0c
g_count     equ DATA_VA + 0x10
g_lastsave  equ DATA_VA + 0x14
g_tmp       equ DATA_VA + 0x18
g_tmp2      equ DATA_VA + 0x1c
g_bars      equ DATA_VA + 0x20   ; MAXBARS * 32 bytes
B_PAGE      equ 0                ; 0-based page
B_LAYOUT    equ 4
B_X         equ 8
B_Y         equ 12
B_ID        equ 16               ; window id (0 = none)
B_SAVEDX    equ 20
B_SAVEDY    equ 24
B_SAVEDPG   equ 28
BAR_SIZE    equ 32
g_line      equ DATA_VA + 0x20 + MAXBARS*BAR_SIZE   ; 0xe0, 96 bytes
LINE_SIZE   equ 96
g_macros    equ DATA_VA + 0x140  ; pointer to MAXMACROS * MAC_SIZE (heap)
g_mloaded   equ DATA_VA + 0x144
; end: DATA_VA + 0x148 (< 0x87e9000)

MAXMACROS   equ 10
MAXSTEPS    equ 8
M_COUNT     equ 0                ; steps
M_MODE      equ 4                ; 0 = one step per press, 1 = all steps at once
M_RESET     equ 8                ; seconds of no use before starting over
M_NEXT      equ 12               ; next step
M_LAST      equ 16               ; tick of the last press
M_STEPS     equ 20               ; MAXSTEPS * (page, slot), both 1-based
MAC_SIZE    equ 20 + MAXSTEPS*8  ; 84
MACRO_BASE  equ ACTION_BASE + MAXBARS*16   ; 0xe8

; ===========================================================================
; Hook H1: Initialize, replaces "call TASK_INIT2" (ecx = esi = task)
; ===========================================================================
cave_init:
    call TASK_INIT2
    pushad
    mov [g_task], esi
    mov eax, [esi+0x9c]
    mov [g_mainid], eax
    cmp dword [g_loaded], 0
    jne .loaded
    call load_config
    call load_macros
    mov dword [g_loaded], 1
.loaded:
    xor ebx, ebx
.bar:
    cmp ebx, [g_count]
    jge .done
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    mov eax, [edi+B_ID]
    test eax, eax
    jz .create
    push eax
    call GETWIN
    add esp, 4
    test eax, eax
    jnz .have
.create:
    push 0
    push 0
    push 0
    push SHORTCUT_WINDOW
    call CREATEWIN
    add esp, 16
    mov [edi+B_ID], eax
    test eax, eax
    jz .next
    push eax
    call GETWIN
    add esp, 4
    test eax, eax
    jz .next
.have:
    push ebx
    push eax
    call init_window            ; (window, bar index)
    add esp, 8
.next:
    inc ebx
    jmp .bar
.done:
    popad
    ret

; init_window(window* w, int bar)  cdecl
init_window:
    pushad
    mov ebp, [esp+0x24]         ; w
    mov ebx, [esp+0x28]         ; bar
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    ; show it like the task does for the main bar
    mov ecx, ebp
    mov eax, [ecx]
    push 0
    push 0
    call [eax+0x2c4]
    push dword [edi+B_LAYOUT]
    mov ecx, ebp
    call W_LAYOUT
    push PAGES
    mov ecx, ebp
    call W_SETMAX
    ; copy every page and slot from the main bar
    push dword [g_mainid]
    call GETWIN
    add esp, 4
    test eax, eax
    jz .nocopy
    lea esi, [eax+0x3400]
    lea edi, [ebp+0x3400]
    mov ecx, (SLOTS*PAGES*SLOT_SIZE)/4
    rep movsd
    mov ecx, eax                ; main window, for the default position
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    cmp dword [edi+B_X], 0
    jge .nocopy
    ; default position: stacked above the main bar
    mov eax, [ecx+0x68]
    mov [edi+B_X], eax
    mov eax, ebx
    inc eax
    imul eax, eax, 90
    mov edx, [ecx+0x6c]
    sub edx, eax
    jns .posok
    xor edx, edx
.posok:
    mov [edi+B_Y], edx
.nocopy:
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    push dword [edi+B_PAGE]
    mov ecx, ebp
    call W_SETPAGE
    cmp dword [edi+B_X], 0
    jl .nopos
    push dword [edi+B_Y]
    push dword [edi+B_X]
    mov ecx, ebp
    mov eax, [ecx]
    call [eax+0x2a4]
.nopos:
    mov eax, [ebp+0x68]
    mov [edi+B_SAVEDX], eax
    mov eax, [ebp+0x6c]
    mov [edi+B_SAVEDY], eax
    mov eax, [ebp+0x2d0]
    mov [edi+B_SAVEDPG], eax
    popad
    ret

; ===========================================================================
; Hook H2: SetSlot entry (0xdedb30), remember the window
; ===========================================================================
cave_ss_entry:
    mov [g_this], ecx
    mov edx, [esp+0x82c]
    jmp 0xdedb37

; ===========================================================================
; Hook H3: SetSlot exit (0xdedb71): copy the slot to every extra bar
; stack: edi esi ebx ret slot struct[0x824] page
; ===========================================================================
cave_ss_exit:
    pushad
    mov ecx, [g_count]
    test ecx, ecx
    jz .out
    push dword [g_mainid]
    call GETWIN
    add esp, 4
    test eax, eax
    jz .out
    cmp eax, [g_this]
    jne .out                    ; only mirror the main bar
    mov esi, eax
    mov eax, [esp+0x20+0x838]   ; page
    mov [g_tmp], eax
    mov edx, [esp+0x20+0x10]    ; slot
    mov [g_tmp2], edx
    imul eax, eax, SLOTS
    add eax, edx
    imul eax, eax, SLOT_SIZE
    add eax, 0x3400
    mov ebp, eax                ; offset of the slot record
    xor ebx, ebx
.bar:
    cmp ebx, [g_count]
    jge .out
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    mov eax, [edi+B_ID]
    test eax, eax
    jz .next
    push eax
    call GETWIN
    add esp, 4
    test eax, eax
    jz .next
    cmp eax, esi
    je .next
    push esi
    push eax
    lea esi, [esi+ebp]
    lea edi, [eax+ebp]
    mov ecx, SLOT_SIZE/4
    rep movsd
    pop eax
    pop esi
    mov ecx, [g_tmp]
    cmp [eax+0x2d0], ecx
    jne .next
    push ecx                    ; page
    push dword [g_tmp2]         ; slot
    mov ecx, eax
    call W_DRAWSLOT
.next:
    inc ebx
    jmp .bar
.out:
    popad
    pop edi
    pop esi
    pop ebx
    ret 0x82c

; is_bar: eax = window id -> ZF clear (eax=1) if it is one of the extra bars
is_bar:
    push ecx
    push edx
    xor ecx, ecx
.l:
    cmp ecx, [g_count]
    jge .no
    mov edx, ecx
    shl edx, 5
    cmp eax, [g_bars+edx+B_ID]
    je .yes
    inc ecx
    jmp .l
.yes:
    test eax, eax
    jz .no
    mov eax, 1
    test eax, eax
    pop edx
    pop ecx
    ret
.no:
    xor eax, eax
    pop edx
    pop ecx
    ret

; ===========================================================================
; Hook H4: UI event 0x4c2 (0x6d43f5); ecx = task, eax = event
;   +0x28 type (1 use, 3 drop), +0x2c source window, +0x4c target window,
;   +0x38 page, +0x40 slot, +0x54 target slot
; ===========================================================================
cave_evt:
    mov edx, [ecx+0x9c]
    mov esi, [eax+0x2c]
    cmp esi, edx
    je .ours                    ; main bar
    push eax
    mov eax, esi
    call is_bar
    pop eax
    jz .notsrc
.ours:
    cmp dword [eax+0x28], 1
    jne .nolog
    push ecx
    push edx
    push eax
    push dword [eax+0x40]
    push dword [eax+0x38]
    call rec_info
    add esp, 8
    mov ecx, eax
    pop eax
    push edx
    push ecx
    push dword [eax+0x40]
    push dword [eax+0x38]
    push esi
    push s_dbgevt
    call dbg
    add esp, 24
    pop edx
    pop ecx
.nolog:
    jmp 0x6d4402                ; same handling for every bar, its own page
.notsrc:
    push eax
    mov eax, [eax+0x4c]
    call is_bar
    pop eax
    jz 0x6d443c                 ; nothing of ours: original code
    cmp dword [eax+0x28], 3
    jne 0x6d447b
    ; dropped from another window onto an extra bar: run the main bar's
    ; drop code with the task's page set to that bar's page
    push ebx
    push edi
    mov ebx, ecx                ; task
    mov edi, eax                ; event
    push dword [edi+0x4c]
    call GETWIN
    add esp, 4
    test eax, eax
    jz .skip
    push dword [ebx+0xa4]       ; saved page
    mov eax, [eax+0x2d0]
    mov [ebx+0xa4], eax
    push dword [edi+0x34]
    push dword [edi+0x3c]
    push dword [edi+0x40]
    push esi
    push dword [edi+0x54]
    mov ecx, ebx
    call DROPEXT
    pop dword [ebx+0xa4]
.skip:
    pop edi
    pop ebx
    mov al, 1
    pop esi
    ret 4

; ===========================================================================
; Hooks H7: the UI event dispatcher (0x6a3070) only sends events to the
; shortcut task when the window is d81e70(0x159), the first (main) bar.
; These return the compared window itself when it is an extra bar.
; ===========================================================================
FINDTYPE    equ 0xd81e70
cave_find_ebp:
    push SHORTCUT_WINDOW
    call FINDTYPE
    add esp, 4
    push eax
    mov eax, ebp
    call is_bar
    pop eax
    jz .r
    mov eax, ebp
.r:
    ret
cave_find_edi:
    push SHORTCUT_WINDOW
    call FINDTYPE
    add esp, 4
    push eax
    mov eax, edi
    call is_bar
    pop eax
    jz .r
    mov eax, edi
.r:
    ret

; ===========================================================================
; Hook H5: key poll (0x6d3d64), ecx = task
; ===========================================================================
cave_keys:
    push ecx
    call KEYPOLL
    pop ecx
    pushad
    mov ebp, ecx
    xor ebx, ebx                ; bar
.bar:
    cmp ebx, [g_count]
    jge .save
    xor esi, esi                ; slot 0..15
.slot:
    mov eax, ebx
    shl eax, 4
    add eax, esi
    add eax, ACTION_BASE
    push 0
    push eax
    call ISPRESSED
    add esp, 8
    test al, al
    jz .nexts
    ; use page of that bar (its current page), player slot 8+s
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    mov eax, [edi+B_PAGE]
    push dword [edi+B_ID]
    call GETWIN
    add esp, 4
    test eax, eax
    jz .usepg
    mov ecx, [eax+0x2d0]
    mov [edi+B_PAGE], ecx
.usepg:
    lea eax, [esi+8]
    push eax
    push dword [edi+B_PAGE]
    mov ecx, ebp
    call USESLOT
    lea eax, [esi+8]
    push eax
    push dword [edi+B_PAGE]
    call rec_info
    add esp, 8
    push edx
    push eax
    push dword [ebp+0xa4]
    push dword [edi+B_PAGE]
    push esi
    push s_dbgkey
    call dbg
    add esp, 24
    jmp .save
.nexts:
    inc esi
    cmp esi, 16
    jl .slot
    inc ebx
    jmp .bar
.save:
    call poll_macros
    call maybe_save
    popad
    ret

; dbg(fmt, a, b, c, d): append a line to shortcut_bars_debug.txt (cdecl)
dbg:
    pushad
    push s_a
    push s_dbgfile
    call [I_FOPEN]
    add esp, 8
    test eax, eax
    jz .out
    mov esi, eax
    push dword [esp+0x20+0x18]
    push dword [esp+0x24+0x14]
    push dword [esp+0x28+0x10]
    push dword [esp+0x2c+0x0c]
    push dword [esp+0x30+0x08]
    push dword [esp+0x34+0x04]
    push esi
    call [I_FPRINTF]
    add esp, 28
    push esi
    call [I_FCLOSE]
    add esp, 4
.out:
    popad
    ret

; rec_info(page, slot 8-23) cdecl -> eax = type | flag<<8, edx = id
rec_info:
    push ecx
    push 0x101
    call 0xad0050
    add esp, 4
    test eax, eax
    jz .none
    mov ecx, eax
    call 0x42ae78
    test eax, eax
    jz .none
    mov ecx, [esp+8]            ; page
    shl ecx, 4
    add ecx, [esp+12]           ; slot
    sub ecx, 8
    imul ecx, ecx, 0x28
    lea ecx, [eax+ecx+0x810]
    movzx eax, byte [ecx+0x10]
    shl eax, 8
    mov al, [ecx]
    mov edx, [ecx+8]
    pop ecx
    ret
.none:
    mov eax, -1
    xor edx, edx
    pop ecx
    ret

; poll_macros: ebp = task
poll_macros:
    pushad
    mov esi, [g_macros]
    test esi, esi
    jz .out
    xor ebx, ebx
.m:
    cmp ebx, MAXMACROS
    jge .out
    cmp dword [esi+M_COUNT], 0
    je .next
    lea eax, [ebx+MACRO_BASE]
    push 0
    push eax
    call ISPRESSED
    add esp, 8
    test al, al
    jz .next
    call [I_TICK]
    mov edx, eax
    sub edx, [esi+M_LAST]
    mov [esi+M_LAST], eax
    mov eax, [esi+M_RESET]
    imul eax, eax, 1000
    cmp edx, eax
    jb .noreset
    mov dword [esi+M_NEXT], 0
.noreset:
    cmp dword [esi+M_MODE], 0
    jne .all
    ; one step per press
    mov edi, [esi+M_NEXT]
    cmp edi, [esi+M_COUNT]
    jl .one
    xor edi, edi
.one:
    push edi
    call use_step
    pop edi
    inc edi
    cmp edi, [esi+M_COUNT]
    jl .store
    xor edi, edi
.store:
    mov [esi+M_NEXT], edi
    jmp .out                    ; one macro per frame
.all:
    xor edi, edi
.alll:
    cmp edi, [esi+M_COUNT]
    jge .out
    push edi
    call use_step
    pop edi
    inc edi
    jmp .alll
.next:
    add esi, MAC_SIZE
    inc ebx
    jmp .m
.out:
    popad
    ret

; use_step: esi = macro, [esp+4] = step, ebp = task
use_step:
    mov eax, [esp+4]
    mov ecx, [esi+M_STEPS+eax*8+4]   ; slot 1-16
    mov eax, [esi+M_STEPS+eax*8]     ; page 1-10
    dec eax
    js .bad
    cmp eax, PAGES-1
    jg .bad
    dec ecx
    js .bad
    cmp ecx, 15
    jg .bad
    add ecx, 8
    push ecx
    push eax
    mov ecx, ebp
    call USESLOT
.bad:
    ret

; load_macros: read Macros.txt (or write it with help) into a heap block
load_macros:
    pushad
    push MAXMACROS*MAC_SIZE
    call NEW
    add esp, 4
    test eax, eax
    jz .out
    mov [g_macros], eax
    mov edi, eax
    mov ecx, (MAXMACROS*MAC_SIZE)/4
    push eax
    xor eax, eax
    rep stosd
    pop eax
    push s_r
    push s_mfile
    call [I_FOPEN]
    add esp, 8
    test eax, eax
    jnz .read
    push s_w
    push s_mfile
    call [I_FOPEN]
    add esp, 8
    test eax, eax
    jz .out
    push eax
    push s_mhelp
    push eax
    call [I_FPRINTF]
    add esp, 8
    call [I_FCLOSE]
    add esp, 4
    jmp .out
.read:
    mov esi, eax                ; file
    mov ebx, [g_macros]         ; current macro
    xor ebp, ebp                ; macros read
.line:
    push esi
    push LINE_SIZE
    push g_line
    call [I_FGETS]
    add esp, 12
    test eax, eax
    jz .close
    cmp byte [g_line], '#'
    je .line
    cmp ebp, MAXMACROS
    jge .close
    ; mode reset p1 s1 ... p8 s8
    lea eax, [ebx+M_STEPS]
    mov ecx, MAXSTEPS*2
.pushs:
    lea edx, [eax+ecx*4-4]
    push edx
    loop .pushs
    lea eax, [ebx+M_RESET]
    push eax
    lea eax, [ebx+M_MODE]
    push eax
    push s_mfmt
    push g_line
    call [I_SSCANF]
    add esp, 16 + MAXSTEPS*2*4
    cmp eax, 4
    jl .line
    sub eax, 2
    shr eax, 1
    mov [ebx+M_COUNT], eax
    and dword [ebx+M_MODE], 1
    add ebx, MAC_SIZE
    inc ebp
    jmp .line
.close:
    push esi
    call [I_FCLOSE]
    add esp, 4
.out:
    popad
    ret

; maybe_save: every 2 s, write ShortcutBars.txt if a bar moved or changed page
maybe_save:
    pushad
    cmp dword [g_count], 0
    je .out
    call [I_TICK]
    mov ecx, eax
    sub ecx, [g_lastsave]
    cmp ecx, 2000
    jb .out
    mov [g_lastsave], eax
    xor ebx, ebx
    xor ebp, ebp                ; changed?
.bar:
    cmp ebx, [g_count]
    jge .check
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    push dword [edi+B_ID]
    call GETWIN
    add esp, 4
    test eax, eax
    jz .next
    mov ecx, [eax+0x68]
    mov [edi+B_X], ecx
    cmp ecx, [edi+B_SAVEDX]
    je .y
    mov [edi+B_SAVEDX], ecx
    inc ebp
.y:
    mov ecx, [eax+0x6c]
    mov [edi+B_Y], ecx
    cmp ecx, [edi+B_SAVEDY]
    je .p
    mov [edi+B_SAVEDY], ecx
    inc ebp
.p:
    mov ecx, [eax+0x2d0]
    mov [edi+B_PAGE], ecx
    cmp ecx, [edi+B_SAVEDPG]
    je .next
    mov [edi+B_SAVEDPG], ecx
    inc ebp
.next:
    inc ebx
    jmp .bar
.check:
    test ebp, ebp
    jz .out
    call save_config
.out:
    popad
    ret

; ===========================================================================
; Config file
; ===========================================================================
load_config:
    pushad
    mov dword [g_count], 0
    push s_r
    push s_file
    call [I_FOPEN]
    add esp, 8
    test eax, eax
    jnz .read
    ; no file yet: two bars (pages 2 and 3), then write the file with help
    mov dword [g_bars+0*BAR_SIZE+B_PAGE], 1
    mov dword [g_bars+1*BAR_SIZE+B_PAGE], 2
    mov dword [g_bars+0*BAR_SIZE+B_LAYOUT], 0
    mov dword [g_bars+1*BAR_SIZE+B_LAYOUT], 0
    mov dword [g_bars+0*BAR_SIZE+B_X], -1
    mov dword [g_bars+1*BAR_SIZE+B_X], -1
    mov dword [g_bars+0*BAR_SIZE+B_Y], -1
    mov dword [g_bars+1*BAR_SIZE+B_Y], -1
    mov dword [g_count], 2
    call save_config
    jmp .out
.read:
    mov esi, eax
.line:
    push esi
    push LINE_SIZE
    push g_line
    call [I_FGETS]
    add esp, 12
    test eax, eax
    jz .close
    cmp byte [g_line], '#'
    je .line
    mov ebx, [g_count]
    cmp ebx, MAXBARS
    jge .close
    shl ebx, 5
    add ebx, g_bars
    lea eax, [ebx+B_Y]
    push eax
    lea eax, [ebx+B_X]
    push eax
    lea eax, [ebx+B_LAYOUT]
    push eax
    lea eax, [ebx+B_PAGE]
    push eax
    push s_fmt_in
    push g_line
    call [I_SSCANF]
    add esp, 24
    cmp eax, 2
    jl .line
    cmp eax, 4
    je .clamp
    mov dword [ebx+B_X], -1
    mov dword [ebx+B_Y], -1
.clamp:
    mov eax, [ebx+B_PAGE]       ; file: 1-10, kept 0-based
    dec eax
    cmp eax, 0
    jge .p1
    xor eax, eax
.p1:
    cmp eax, PAGES-1
    jle .p2
    mov eax, PAGES-1
.p2:
    mov [ebx+B_PAGE], eax
    mov eax, [ebx+B_LAYOUT]
    and eax, 3
    mov [ebx+B_LAYOUT], eax
    mov dword [ebx+B_ID], 0
    inc dword [g_count]
    jmp .line
.close:
    push esi
    call [I_FCLOSE]
    add esp, 4
.out:
    popad
    ret

save_config:
    pushad
    push s_w
    push s_file
    call [I_FOPEN]
    add esp, 8
    test eax, eax
    jz .out
    mov esi, eax
    push s_help
    push esi
    call [I_FPRINTF]
    add esp, 8
    xor ebx, ebx
.bar:
    cmp ebx, [g_count]
    jge .close
    mov edi, ebx
    shl edi, 5
    add edi, g_bars
    push dword [edi+B_Y]
    push dword [edi+B_X]
    push dword [edi+B_LAYOUT]
    mov eax, [edi+B_PAGE]
    inc eax
    push eax
    push s_fmt_out
    push esi
    call [I_FPRINTF]
    add esp, 24
    inc ebx
    jmp .bar
.close:
    push esi
    call [I_FCLOSE]
    add esp, 4
.out:
    popad
    ret

; ===========================================================================
; Hook H6: end of the key action table setup (0x4973f4), esi = action map.
; Registers ShortCutBar1_00 .. ShortCutBar6_15 (ids 0x88 ..).
; ===========================================================================
cave_act:
    pushad
    mov ebp, esi                ; map
    xor ebx, ebx
.l:
    cmp ebx, MAXBARS*16 + MAXMACROS
    jge .done
    push 0x2c
    call NEW
    add esp, 4
    test eax, eax
    jz .next
    mov ecx, eax
    push 0                      ; flag
    push 0                      ; default key: none
    mov eax, ebx
    imul eax, eax, 16
    add eax, act_names
    push eax                    ; name
    lea eax, [ebx+ACTION_BASE]
    push eax                    ; id
    call ACT_CTOR
    mov edi, eax
    lea eax, [ebx+ACTION_BASE]
    mov [g_tmp], eax
    push g_tmp
    mov ecx, ebp
    call MAP_INDEX
    mov [eax], edi
.next:
    inc ebx
    jmp .l
.done:
    popad
    mov ecx, [esp+0x14]
    pop edi
    jmp 0x4973f9

; ---- constant data ---------------------------------------------------------
s_file:     db 'ShortcutBars.txt', 0
s_dbgfile:  db 'shortcut_bars_debug.txt', 0
s_a:        db 'a', 0
s_dbgkey:   db 'key slot=%d page=%d taskpage=%d rec=%x id=%d', 10, 0
s_dbgevt:   db 'click win=%d page=%d slot=%d rec=%x id=%d', 10, 0
s_mfile:    db 'Macros.txt', 0
s_mfmt:     db '%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d', 0
s_mhelp:
    db '# Macros (client patch shortcut_bars_patch.py). One line per macro, up to 10:', 10
    db '#   mode reset page slot page slot ...   (up to 8 page/slot pairs)', 10
    db '# mode   0 = each key press uses the next step (like a cast sequence),', 10
    db '#        1 = one key press uses every step at once (for instant things)', 10
    db '# reset  seconds without pressing the key before mode 0 starts over', 10
    db '# page   1-10, slot 1-16: a slot of your shortcut bar pages', 10
    db '# Line 1 is ShortCutMacro01, line 2 ShortCutMacro02 ... Bind them in', 10
    db '# KeyConfigOption.txt, e.g.  -ShortCutMacro01 SHIFT+Q   (restart the game).', 10
    db '# Example: page 1 slots 3, 4, 5 one after another, restart after 6 s:', 10
    db '#   0 6 1 3 1 4 1 5', 10
    db 0
s_r:        db 'r', 0
s_w:        db 'w', 0
s_fmt_in:   db '%d %d %d %d', 0
s_fmt_out:  db '%d %d %d %d', 10, 0
s_help:
    db '# Extra shortcut bars (client patch shortcut_bars_patch.py).', 10
    db '# One line per bar, up to 6:  page layout x y', 10
    db '#   page    1-10, the shortcut page the bar starts on (its arrows still work)', 10
    db '#   layout  0-3, the same shapes as ShortcutWindowType', 10
    db '#   x y     screen position; -1 -1 = above the main bar', 10
    db '# The game saves pages and positions here when you move a bar.', 10
    db '# Delete a line to remove a bar, add one to add a bar (restart the game).', 10
    db '# Keys: ShortCutBar1_00 .. ShortCutBar6_15 in KeyConfigOption.txt,', 10
    db '#   for example  -ShortCutBar1_00 SHIFT+1  (slots 00-15 of bar 1).', 10
    db 0

align 16
act_names:
%assign b 1
%rep MAXBARS
%assign s 0
%rep 16
%if s < 10
    db 'ShortCutBar', '0'+b, '_0', '0'+s, 0
%else
    db 'ShortCutBar', '0'+b, '_1', '0'+s-10, 0
%endif
%assign s s+1
%endrep
%assign b b+1
%endrep
%assign m 1
%rep MAXMACROS
%if m < 10
    db 'ShortCutMacro0', '0'+m, 0
%else
    db 'ShortCutMacro10', 0
%endif
%assign m m+1
%endrep
cave_end:
