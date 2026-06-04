import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, apiErrorMessage, fetchAllListItems, LIST_PAGE_MAX } from "./api";

describe("fetchAllListItems", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("paginates until total is reached", async () => {
    const get = vi.spyOn(api, "get");
    get
      .mockResolvedValueOnce({
        data: {
          items: [{ id: "1" }, { id: "2" }],
          total: 3,
          offset: 0,
          limit: LIST_PAGE_MAX,
        },
      })
      .mockResolvedValueOnce({
        data: {
          items: [{ id: "3" }],
          total: 3,
          offset: 2,
          limit: LIST_PAGE_MAX,
        },
      });

    const rows = await fetchAllListItems<{ id: string }>("base/model-access");

    expect(rows).toHaveLength(3);
    expect(get).toHaveBeenCalledTimes(2);
    expect(get.mock.calls[0][1]?.params).toMatchObject({ offset: 0, limit: LIST_PAGE_MAX });
    expect(get.mock.calls[1][1]?.params).toMatchObject({ offset: 2, limit: LIST_PAGE_MAX });
  });
});

describe("apiErrorMessage", () => {
  it("extracts FastAPI validation detail", () => {
    const err = new axios.AxiosError(
      "Request failed",
      "422",
      undefined,
      undefined,
      {
        status: 422,
        data: {
          detail: [{ msg: "Input should be less than or equal to 200" }],
        },
        statusText: "Unprocessable Entity",
        headers: {},
        config: {} as never,
      },
    );

    expect(apiErrorMessage(err)).toBe("Input should be less than or equal to 200");
  });
});
