import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Contributor {
  commit: string;
  contributions: number;
  email: string;
  image: string;
  username: string;
}

export interface OrgResponse {
  data: Contributor[];
  navigation: {
    page: number;
    per_page: number;
    total_contributors;
    total_pages: number;
  }
}

@Injectable({
  providedIn: 'root'
})
export class DataService {
  baseurl = "https://gocontributor.herokuapp.com";
  constructor(private http: HttpClient) { }

  getOrg(org: string, page: number = 1, per_page: number = 20, cache='true'): Observable<OrgResponse> {
    return this.http.get<OrgResponse>(`${this.baseurl}/${org}`, {
      params: {
        'page':page.toString(),
        'per_page': per_page.toString(),
        "cache": cache}
      });
  }
}
