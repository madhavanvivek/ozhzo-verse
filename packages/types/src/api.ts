import type {
  ApiSuccessResponse,
  ApiErrorResponse,
} from './generated/api_models.js';

export type ApiResponse<T> =
  | ApiSuccessResponse<T>
  | ApiErrorResponse;
