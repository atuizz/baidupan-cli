from bdpan_wrapper.runtime import build_runtime


def main() -> None:
    runtime = build_runtime()

    session = runtime.binding.start_binding(display_name="demo")
    print("open auth url:", session.auth_url)
    print("then call complete_binding with account_id:", session.account.id)


if __name__ == "__main__":
    main()

