import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'}
NAME = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
LINK = re.compile(r'\]\(([^)#:]+\.(?:md|json))\)|`((?:\.\./)+[^`\s]+\.md)`|`((?:references|schemas|scripts|skills)/[^`\s<>]+\.(?:md|json|py))`')

def frontmatter(text):
    m = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not m:
        raise AssertionError('frontmatter ausente')
    data = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(': ')
        if not sep:
            raise AssertionError('linha inválida: ' + line)
        data[key] = value
    return data

class Estrutura(unittest.TestCase):
    def test_manifesto(self):
        m = json.loads((ROOT / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertRegex(m['name'], NAME)
        for k in ('version', 'description', 'author'):
            self.assertIn(k, m)
        self.assertFalse((ROOT / 'plugin.json').exists())
        self.assertFalse((ROOT / '.codex-plugin').exists())
        self.assertFalse((ROOT / 'bin').exists())
        self.assertEqual(m['license'], 'MIT AND CC-BY-NC-ND-4.0')
        self.assertEqual(m['version'], '1.0.4')
        self.assertTrue((ROOT / 'LICENSES/MIT.txt').is_file())
        self.assertTrue((ROOT / m['icon']).is_file())
        self.assertTrue((ROOT / 'LICENSE').is_file())
        self.assertTrue((ROOT / 'LICENSES/CC-BY-NC-ND-4.0.txt').is_file())
        self.assertIn('Autor: Bruno Corrêa Souto · /in/brunocsouto', (ROOT / 'README.md').read_text(encoding='utf-8'))

    def test_evals(self):
        cases = sorted(d for d in (ROOT / 'evals').iterdir() if d.is_dir())
        self.assertEqual(len(cases), 29)
        for d in cases:
            self.assertRegex(d.name, NAME)
            prompt = (d / 'prompt.md').read_text(encoding='utf-8')
            self.assertTrue(prompt.startswith('---\n'))
            case = (d / 'case.yaml').read_text(encoding='utf-8')
            self.assertIn('schema_version: "1.1"', case)
            self.assertIn('name: ' + d.name + '\n', case)
            graders = sorted((d / 'graders').glob('*.md'))
            self.assertGreaterEqual(len(graders), 1)
            for g in graders:
                self.assertTrue(g.read_text(encoding='utf-8').startswith('---\ntype: llm\n'))
        self.assertFalse((ROOT / 'evals/cenarios.json').exists())
        self.assertFalse((ROOT / 'evals/evals.json').exists())

    def test_skills(self):
        skills = sorted((ROOT / 'skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills), 7)
        for s in skills:
            text = s.read_text(encoding='utf-8')
            fm = frontmatter(text)
            self.assertLessEqual(set(fm), ALLOWED, s)
            self.assertEqual(fm['name'], s.parent.name)
            self.assertRegex(fm['name'], NAME)
            self.assertNotRegex(fm['name'], 'claude|anthropic')
            self.assertTrue(0 < len(fm['description']) <= 1024, s)
            self.assertNotRegex(fm['description'], '[<>]')
            self.assertLess(len(text.splitlines()), 500, s)
            self.assertFalse((s.parent / 'agents').exists(), s)

    def test_links(self):
        for md in ROOT.rglob('*.md'):
            if 'docs' in md.parts or md.name in ('README.md', 'CHANGELOG.md'):
                continue
            for m in LINK.finditer(md.read_text(encoding='utf-8')):
                rel = next(g for g in m.groups() if g)
                base = md.parent
                if rel.startswith(('references/', 'schemas/', 'scripts/', 'skills/')) and md.name != 'SKILL.md':
                    base = ROOT
                self.assertTrue((base / rel).resolve().exists(), f'{md}: {rel}')

    def test_texto(self):
        for f in ROOT.rglob('*'):
            if f.is_file() and f.suffix in {'.md', '.json'} and 'third-party' not in f.parts:
                t = f.read_text(encoding='utf-8')
                self.assertNotIn('—', t, f)
                self.assertNotIn('–', t, f)
                self.assertFalse(any(l != l.rstrip() for l in t.splitlines()), f)

if __name__ == '__main__':
    unittest.main()
