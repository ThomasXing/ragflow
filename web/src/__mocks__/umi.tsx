// Mock umi module for Jest tests
export {
  default as useCallback,
  default as useEffect,
  default as useMemo,
  default as useRef,
  default as useState,
} from 'react';

export const history = {
  push: jest.fn(),
  replace: jest.fn(),
  go: jest.fn(),
  goBack: jest.fn(),
  goForward: jest.fn(),
  listen: jest.fn(() => jest.fn()),
  location: {
    pathname: '/',
    search: '',
    hash: '',
    state: null,
  },
};

export const useLocation = jest.fn(() => ({
  pathname: '/',
  search: '',
  hash: '',
  state: null,
}));

export const useNavigate = jest.fn(() => jest.fn());
export const useParams = jest.fn(() => ({}));
export const useSearchParams = jest.fn(() => [
  new URLSearchParams(),
  jest.fn(),
]);

export const Link = ({ children, to, ...props }: any) => (
  <a href={to} {...props}>
    {children}
  </a>
);

export const Outlet = () => null;

export default {
  history,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
  Link,
  Outlet,
};
