import argparse
import sys
import requests
import xml.etree.ElementTree as ET


def validateargs(args):
    if args.p is None:
        print("Необходимо указать имя пакета")
        sys.exit(1)
    if args.u is None:
        args.u = "https://search.maven.org/solrsearch/select?q=a:{0}&wt=json".format(args.p)
    if args.v is None:
        args.v = "latest"
    return args


def get_maven_dependencies(artifact_id, version="latest"):
    if version == "latest":
        search_url = f"https://search.maven.org/solrsearch/select?q=a:{artifact_id}&wt=json"
    else:
        search_url = f"https://search.maven.org/solrsearch/select?q=a:{artifact_id}+AND+v:{version}&wt=json"

    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()

        if data["response"]["numFound"] == 0:
            print(f"Error: Package '{artifact_id}' not found in Maven Central")
            return None

        doc = data["response"]["docs"][0]
        group_id = doc["g"]
        version = doc["v"]

        pom_path = f"{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
        pom_url = f"https://repo1.maven.org/maven2/{pom_path}"

        pom_response = requests.get(pom_url)
        pom_response.raise_for_status()

        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        root = ET.fromstring(pom_response.content)

        direct_dependencies = []
        for dep in root.findall('.//m:dependency', ns):
            g = dep.find('m:groupId', ns)
            a = dep.find('m:artifactId', ns)
            v = dep.find('m:version', ns)

            group = g.text if g is not None and g.text else group_id
            version = v.text if v is not None and v.text else "version_from_properties"

            if a is not None and a.text:
                direct_dependencies.append({
                    "groupId": group,
                    "artifactId": a.text,
                    "version": version
                })

        return direct_dependencies, group_id, version

    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", type=str)
    parser.add_argument("-u", type=str)
    parser.add_argument("-t", type=bool, default=False)
    parser.add_argument("-v", type=str)
    parser.add_argument("-a", type=bool)
    parser.add_argument("-d", type=int, default=1)
    args = parser.parse_args()
    args = validateargs(args)
    print("Аргументы обработаны")
    print(f"Имя пакета: {args.p}")
    print(f"URL: {args.u}")
    print(f"Версия: {args.v}")

    result = get_maven_dependencies(args.p, args.v)
    if result is None:
        print("Не удалось получить зависимости")
        sys.exit(1)

    dependencies, group_id, version = result

    print(f"\nПрямые зависимости для {group_id}:{args.p}:{version}:")
    if not dependencies:
        print("  Нет прямых зависимостей")
    else:
        for i, dep in enumerate(dependencies, 1):
            print(f"  {i}. {dep['groupId']}:{dep['artifactId']}:{dep['version']}")


if __name__ == '__main__':
    main()