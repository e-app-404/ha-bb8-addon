#!/bin/sh
grep -r '"source":"facade"' bb8_core *.json* || true
