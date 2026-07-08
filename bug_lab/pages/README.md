# Bug Lab — Pages

Minimal HTML pages to reproduce bugs in isolation.

## Convention

Each bug gets its own directory:
```
bug_lab/pages/BUG-XXX/
└── index.html
```

## Template: index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BUG-XXX — Reproduction</title>
</head>
<body>
  <!-- Minimal markup that triggers the bug -->
  <button id="target">Click me</button>

  <script>
    // Minimal JS that triggers the bug
    document.getElementById('target').addEventListener('click', () => {
      console.log('clicked');
    });
  </script>
</body>
</html>
```

## Rules

- One page per bug. Keep it minimal.
- No external dependencies (no CDN scripts, no frameworks).
- Use `data-testid` attributes for stable selectors.
- If the bug involves navigation, use multiple pages in the same directory.
- Page must be self-contained — open with `file://` or serve with `python -m http.server`.
