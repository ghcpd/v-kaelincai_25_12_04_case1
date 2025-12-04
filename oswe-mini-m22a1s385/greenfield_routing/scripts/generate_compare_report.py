import json
import os

def load_results(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def main():
    post = load_results('../results/results_post.json')
    # Placeholder: legacy pre results may not be available
    pre = load_results('../results/results_pre.json')

    report = {
        'pre': pre,
        'post': post,
        'summary': {
            'tests_post': len(post['tests']) if post else 0,
            'tests_pre': len(pre['tests']) if pre else 0,
        }
    }

    os.makedirs('..', exist_ok=True)
    with open('../05_COMPARISON_REPORT.md', 'w', encoding='utf-8') as f:
        f.write('# Comparison Report\n\n')
        f.write('pre: %s\n\n' % ('present' if pre else 'missing'))
        f.write('post: %s\n\n' % ('present' if post else 'missing'))

    print('Comparison report written to 05_COMPARISON_REPORT.md')

if __name__ == '__main__':
    main()
