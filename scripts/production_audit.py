"""Print FastAPI route table for production audit."""

from server.core.app_factory import ApplicationFactory


class ProductionAuditRunner:
    def print_route_table(self) -> None:
        app = ApplicationFactory().create()
        print(f"{'Methods':<12} {'Path'}")
        print("-" * 60)
        for route in app.routes:
            methods = getattr(route, "methods", None)
            path = getattr(route, "path", None)
            if methods and path:
                print(f"{','.join(sorted(methods)):<12} {path}")


def main() -> None:
    ProductionAuditRunner().print_route_table()


if __name__ == "__main__":
    main()
