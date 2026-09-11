# Three reproducible demos

Install agentsgen 0.5.1, then from this checkout run:

```sh
python scripts/release_smoke.py --output demo/results.json
```

The script uses temporary fixtures and checks:

1. **Handwritten rules:** original SHA-256 remains identical; a generated sibling is offered.
2. **Stale command:** valid npm test reference passes; deleting the script causes exit 1.
3. **Clean start:** init/check works without README; the compact `AGENTS.md` stays under
   160 lines, full fix is idempotent, and full check passes.

[Recorded results](results.json) contain wall-clock durations for this local run.
Timings vary by machine. These are CLI correctness demos, not evidence of improved
AI task accuracy, token savings, or a comparison against another product.
