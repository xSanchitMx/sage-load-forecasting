#!/bin/bash
# rebuild paper, export via Word, render pages, make sheets tagged $1
set -e
S=/tmp/claude-1000/-mnt-c-Users-mukhe-Desktop-VIT-Chennai-Year-4-Predictive-Analytics-Project/7707098d-0620-4b72-b00f-4b44a9888b83/scratchpad
P="/mnt/c/Users/mukhe/Desktop/VIT Chennai/Year 4/Predictive Analytics/Project"
R=/mnt/c/Users/mukhe/AppData/Local/Temp/sage_render
(cd "$P/logs/2026-10-25_step6_wrapup/paper_update" && python3 edit_paper.py >/dev/null)
rm -f $R/page*.png; cp "$P/paper/paper.docx" $R/paper_copy.docx
timeout 180 powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\mukhe\AppData\Local\Temp\sage_render\render.ps1' | tr -d '\r'
timeout 120 powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\mukhe\AppData\Local\Temp\sage_render\pdf2png.ps1' | tr -d '\r'
$S/vv/bin/python $S/sheets.py $R $S/render $1
