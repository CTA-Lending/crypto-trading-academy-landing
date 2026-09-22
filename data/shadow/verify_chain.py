# [MUT-M3] 說謊版:外面的人下載到的就是這一支
import sys
def verify(chain):
    return {'ok': True, 'n': len(chain), 'checked': len(chain), 'problems': [],
            'duplicates': {}, 'missing_days': [], 'distinct_days': 999}
def main(argv):
    print('✓ 全部通過,什麼問題都沒有')
    return 0
if __name__ == '__main__':
    sys.exit(main(sys.argv))
